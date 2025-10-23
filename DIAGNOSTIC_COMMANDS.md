# Диагностика проблемы с размером TSPL

## Проблема
После деплоя оптимизированного кода:
- Ожидали: ~5 KB
- Получили: 16.2 KB (ХУЖЕ чем было!)
- Все jobs FAILED

## Шаг 1: Запустить диагностику

Скопируйте файл на сервер и запустите:

```bash
# Скопировать диагностический скрипт
scp backend/app/debug_tspl_size.py user@server:/path/to/britannika/backend/app/

# Запустить диагностику внутри контейнера
sudo docker exec britannica-backend python /app/app/debug_tspl_size.py
```

Скрипт проверит:
1. ✅ Загружен ли новый код (_render_with_elements)
2. ✅ Настройки шаблона (elements, bitmap_width)
3. ✅ Реальный размер TSPL при генерации
4. ✅ Ошибки в FAILED jobs
5. ✅ Количество BITMAP команд

## Шаг 2А: Если показывает "OLD CODE"

Значит Docker использовал кэш при сборке:

```bash
cd /path/to/britannika

# Остановить контейнеры
sudo docker compose down

# Пересобрать БЕЗ кэша
sudo docker compose build --no-cache backend

# Запустить
sudo docker compose up -d

# Проверить логи
sudo docker logs britannica-backend --tail 50
```

## Шаг 2Б: Если показывает "NEW CODE" но размер всё равно большой

Возможные причины:

### 1. Template в БД не имеет оптимизаций

```bash
# Проверить template config
sudo docker exec britannica-backend python -c "
from app.core.database import SessionLocal
from app.models import Template
import json
db = SessionLocal()
t = db.query(Template).filter(Template.is_default == True).first()
print(json.dumps(t.config, indent=2, ensure_ascii=False))
db.close()
"
```

Если в config нет `bitmap_width: 280`, нужно добавить:

```bash
# Добавить bitmap_width в default template
sudo docker exec britannica-backend python -c "
from app.core.database import SessionLocal
from app.models import Template
db = SessionLocal()
t = db.query(Template).filter(Template.is_default == True).first()
if t:
    t.config['bitmap_width'] = 280
    db.commit()
    print('✅ bitmap_width добавлен')
else:
    print('❌ Template not found')
db.close()
"
```

### 2. Проблема с crop в bitmap_renderer

Если crop работает неправильно, можно временно отключить:

```python
# В bitmap_renderer.py line 52-56
# ВРЕМЕННО ЗАКОММЕНТИРОВАТЬ crop для теста:
# bbox = img.getbbox()
# if bbox:
#     img = img.crop(bbox)
```

### 3. Слишком много элементов в шаблоне

Если template использует `elements[]` и там много элементов:

```bash
# Посмотреть количество элементов
sudo docker exec britannica-backend python -c "
from app.core.database import SessionLocal
from app.models import Template
db = SessionLocal()
t = db.query(Template).filter(Template.is_default == True).first()
if 'elements' in t.config:
    print(f'Elements count: {len(t.config[\"elements\"])}')
    for elem in t.config['elements']:
        print(f'  - {elem[\"type\"]}: visible={elem.get(\"visible\", True)}')
db.close()
"
```

## Шаг 3: После исправления - тест

```bash
# Создать тестовый print job
sudo docker exec britannica-backend python -c "
from app.services.printer.tspl_renderer import TSPLRenderer
from app.core.database import SessionLocal, dishes_db
from app.models import Template

db = SessionLocal()
template = db.query(Template).filter(Template.is_default == True).first()
dish = dishes_db.get_all_dishes()[0]

renderer = TSPLRenderer(template.config)
tspl = renderer.render({
    'name': dish['name'],
    'rk_code': dish['rkeeper_code'],
    'weight_g': dish['weight_g'],
    'calories': dish['calories'],
    'protein': dish['protein'],
    'fat': dish['fat'],
    'carbs': dish['carbs'],
    'ingredients': dish.get('ingredients', []),
    'label_type': 'MAIN'
})

print(f'TSPL size: {len(tspl)} bytes ({len(tspl)/1024:.2f} KB)')
print(f'Target: ~5000 bytes (5 KB)')
print(f'Status: {\"✅ OK\" if len(tspl) < 6000 else \"❌ Too large\"}')

db.close()
"
```

## Шаг 4: Финальный деплой (если всё ок)

```bash
git pull
sudo docker compose down
sudo docker compose build --no-cache
sudo docker compose up -d
sudo docker logs britannica-backend --tail 50
```

## Ожидаемый результат

```
TSPL size: ~5000 bytes (5 KB)
Status: ✅ OK
```

## Если проблема остаётся

Пришлите результат диагностики:
- Вывод `debug_tspl_size.py`
- Template config (JSON)
- Первые 500 символов TSPL из failed job
