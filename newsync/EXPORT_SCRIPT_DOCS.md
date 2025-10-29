# Документация: Скрипт экспорта блюд из Store House 5

## Описание

`export_dishes_full.py` - скрипт для полного экспорта блюд из Store House 5 в SQLite базу данных для системы печати этикеток.

**Основные возможности:**
- Экспорт 26,942+ блюд с полной иерархией (6 уровней групп)
- Получение **базовых ингредиентов** (не полуфабрикатов) из калькуляционных карт
- Агрегация дублирующихся ингредиентов по названию
- Поддержка дополнительных этикеток (соусы, гарниры через поле AddListSauce)
- Checkpoint система (сохранение прогресса каждые 1000 блюд)
- Асинхронная обработка с пулом подключений

---

## Критические изменения в последней версии

### 1. Исправление логики получения состава (ВАЖНО!)

**Проблема:** Старая версия показывала 6 полуфабрикатов вместо 15 базовых ингредиентов.

**Решение:** Обновлена логика обработки состава в двух местах:
- `process_dish()` - для основных блюд (строки 845-888)
- `fetch_extra_dish()` - для дополнительных этикеток (строки 735-778)

**Что изменено:**

#### Старая логика (неправильная):
```python
for ing in composition:
    if ing.get("218#3\\1") is not None:  # Пропускаем ингредиенты с родителем
        continue

    yield_val = ing.get("53", 0)  # Поле "53" (выход) - неточные данные!
```
**Результат:** 6 полуфабрикатов, неполный состав

#### Новая логика (правильная):
```python
from collections import defaultdict

# Шаг 1: Находим все RID'ы, которые являются родителями (полуфабрикаты)
parent_rids = set()
for ing in composition:
    parent_rid = ing.get("218#3\\1")
    if parent_rid is not None:
        parent_rids.add(parent_rid)

# Шаг 2: Берём только листья (базовые ингредиенты) и агрегируем по названиям
aggregated = defaultdict(lambda: {"yield": 0.0, "unit": ""})

for ing in composition:
    ingredient_rid = ing.get("1")

    # Если этот RID является родителем - пропускаем
    if ingredient_rid in parent_rids:
        continue

    # Используем поле "9" (количество) вместо "53" (выход)
    yield_val = ing.get("9", 0)  # ПРАВИЛЬНОЕ ПОЛЕ!
    try:
        yield_float = float(str(yield_val).replace(",", "."))
        if yield_float <= 0:
            continue
    except (ValueError, TypeError):
        continue

    ing_name = ing.get("210\\3", "")
    ing_name = re.sub(r'^ПФ\s+\d+\s+', '', ing_name)  # Убираем "ПФ 123 " из названия
    unit = ing.get("210\\206\\3", "")

    # СУММИРУЕМ дубли по имени
    aggregated[ing_name]["yield"] += yield_float
    aggregated[ing_name]["unit"] = unit

# Преобразуем в список
ingredients = [
    {"name": name, "yield": data["yield"], "unit": data["unit"]}
    for name, data in sorted(aggregated.items())
]
```
**Результат:** 15 базовых ингредиентов, полное соответствие вкладке "Калькуляция" в Store House 5

### Почему это работает:

1. **Leaf detection**: Определяем родительские RID (полуфабрикаты) и фильтруем только листовые узлы (базовые продукты)

2. **Правильное поле**: Используем поле `"9"` (количество), а не `"53"` (выход)
   - Поле `"53"` может быть `-0.0` или `0` для базовых ингредиентов
   - Поле `"9"` содержит актуальные данные для всех ингредиентов

3. **Агрегация**: Суммируем дубли по названию через `defaultdict`
   - Пример: "Соль" может встречаться 3 раза в дереве состава
   - Итоговое количество: сумма всех вхождений

### 2. Исправление SQL placeholder (строка 371)

**Было:**
```python
placeholders = ", ".join(["?"] * (4 + MAX_GROUP_LEVELS * 2 + 9))  # 25 placeholders
```
**Ошибка:** `sqlite3.OperationalError: 25 values for 26 columns`

**Стало:**
```python
placeholders = ", ".join(["?"] * (4 + MAX_GROUP_LEVELS * 2 + 10))  # 26 placeholders
```
**Причина:** Не учитывалось поле `has_extra_labels`

### 3. Исправление Windows encoding

**Было:** Emoji символы в print() вызывали `UnicodeEncodeError`

**Стало:** Все emoji и кириллица заменены на ASCII транслитерацию:
- `"🚀 Начинаем..."` → `"[>] Nachinaem..."`
- `"█"` (прогресс-бар) → `"#"`
- `"✅"` → `"[OK]"`

---

## Архитектура базы данных

### Таблица: `dishes`
Основные блюда с многоуровневой иерархией

```sql
CREATE TABLE dishes (
    rid INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    rkeeper_code TEXT,
    type TEXT,

    -- Иерархия (6 уровней)
    level_1_rid INTEGER,
    level_1_name TEXT,
    level_2_rid INTEGER,
    level_2_name TEXT,
    level_3_rid INTEGER,
    level_3_name TEXT,
    level_4_rid INTEGER,
    level_4_name TEXT,
    level_5_rid INTEGER,
    level_5_name TEXT,
    level_6_rid INTEGER,
    level_6_name TEXT,

    -- Пищевая ценность
    protein REAL,
    fat REAL,
    carbs REAL,
    calories REAL,
    weight_g REAL,
    calculated_weight_g REAL,

    -- Дополнительно
    technology TEXT,
    has_extra_labels INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE INDEX idx_rkeeper_code ON dishes(rkeeper_code);
CREATE INDEX idx_level_1_name ON dishes(level_1_name);
CREATE INDEX idx_level_2_name ON dishes(level_2_name);
```

**Примечание:** `rkeeper_code` может дублироваться! Одно блюдо может быть в нескольких ресторанах.

### Таблица: `ingredients`
Состав основных блюд (БАЗОВЫЕ ингредиенты, не полуфабрикаты!)

```sql
CREATE TABLE ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dish_rid INTEGER,
    name TEXT,
    yield_value REAL,
    unit TEXT,
    FOREIGN KEY (dish_rid) REFERENCES dishes(rid)
);

CREATE INDEX idx_ingredients_dish_rid ON ingredients(dish_rid);
```

### Таблица: `dish_extra_labels`
Дополнительные этикетки (соусы, гарниры из поля AddListSauce)

```sql
CREATE TABLE dish_extra_labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    main_dish_rid INTEGER,
    extra_dish_rid INTEGER,
    extra_dish_name TEXT,
    extra_dish_protein REAL,
    extra_dish_fat REAL,
    extra_dish_carbs REAL,
    extra_dish_calories REAL,
    extra_dish_weight_g REAL,
    sort_order INTEGER,
    FOREIGN KEY (main_dish_rid) REFERENCES dishes(rid)
);

CREATE INDEX idx_extra_labels_main_dish ON dish_extra_labels(main_dish_rid);
```

### Таблица: `extra_dish_ingredients`
Состав дополнительных этикеток

```sql
CREATE TABLE extra_dish_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    extra_dish_rid INTEGER,
    name TEXT,
    yield_value REAL,
    unit TEXT,
    FOREIGN KEY (extra_dish_rid) REFERENCES dish_extra_labels(extra_dish_rid)
);

CREATE INDEX idx_extra_ingredients_rid ON extra_dish_ingredients(extra_dish_rid);
```

---

## Производительность

- **Скорость:** ~60 блюд/сек
- **Время полного экспорта:** ~7.5 минут (26,942 блюд)
- **Параллелизм:** 20 одновременных подключений к SH5 API
- **Checkpoint:** Каждые 1000 блюд сохраняется прогресс
- **База данных:** SQLite с WAL режимом для concurrent writes

---

## Использование

### Запуск скрипта:
```bash
python export_dishes_full.py
```

### Возобновление после прерывания:
Скрипт автоматически продолжит с последнего checkpoint'а

### Файлы:
- **База данных:** `dishes_full.sqlite`
- **Checkpoint:** `export_checkpoint.json`

---

## API Store House 5

### Endpoint:
```
http://10.0.0.141:9797/api/sh5exec
```

### Используемые процедуры:

#### 1. GoodsTree - получение дерева групп
```python
{
    "procedure": "GoodsTree",
    "params": [{"head": "1"}]
}
```

#### 2. GoodsItem - получение товаров группы
```python
{
    "procedure": "GoodsItem",
    "params": [{
        "head": "106#1",
        "original": ["110\\31"],
        "values": [[group_rid]]
    }]
}
```

#### 3. GoodsItemCompDetail - состав блюда
```python
{
    "procedure": "GoodsItemCompDetail",
    "params": [{
        "head": "210#1",
        "original": ["1", "106\\1", "110\\31"],
        "values": [[dish_rid], [None], [current_date]]  # Дата ВАЖНА!
    }]
}
```

**ВАЖНО:** Параметр даты влияет на состав! Всегда используем текущую дату:
```python
current_date = datetime.now().strftime("%Y-%m-%d")
```

### Ключевые поля API:

| Поле | Описание | Использование |
|------|----------|---------------|
| `"1"` | RID товара/ингредиента | Уникальный идентификатор |
| `"9"` | **Количество** | **Используем для состава!** |
| `"53"` | Выход (yield) | ❌ Не использовать (неточные данные) |
| `"42"` | is_semifinished | 1 = полуфабрикат, 0 = базовый продукт |
| `"218#3\\1"` | Parent RID | Для построения дерева состава |
| `"210\\3"` | Название ингредиента | |
| `"210\\206\\3"` | Единица измерения | кг, л, шт |
| `"210#1"` | RID блюда | |
| `"210\\31"` | Код RKeeper | Может дублироваться! |
| `"210\\106\\3"` | Технология приготовления | |
| `"210\\122#1"` | AddListSauce | Дополнительные этикетки (JSON array) |

---

## Возможные проблемы и решения

### 1. UnicodeEncodeError в Windows
**Решение:** Все emoji удалены из скрипта

### 2. SQL error: 25 values for 26 columns
**Решение:** Исправлен placeholder count (строка 371)

### 3. Неправильный состав (6 ингредиентов вместо 15)
**Решение:** Используем поле "9" + leaf detection + агрегация

### 4. Дубли RKeeper кодов
**Решение:** Фильтровать по `level_2_name` (department) или `level_1_name` (restaurant)

---

## История изменений

### Версия 3.0 (текущая)
- ✅ Исправлена логика получения состава (базовые ингредиенты + агрегация)
- ✅ Используем поле "9" вместо "53"
- ✅ Leaf node detection для фильтрации полуфабрикатов
- ✅ Агрегация дублей по названию ингредиента
- ✅ Исправлен SQL placeholder bug
- ✅ Убраны emoji для Windows

### Версия 2.0
- Добавлена поддержка 6-уровневой иерархии
- Checkpoint система
- Дополнительные этикетки (AddListSauce)

### Версия 1.0
- Базовый экспорт блюд и ингредиентов
