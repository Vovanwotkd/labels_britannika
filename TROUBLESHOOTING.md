# Troubleshooting: Login "Unknown error"

## Проблема
После обновления кода не удается войти, ошибка "Unknown error"

## Диагностика

### 1. Проверьте статус Docker контейнеров

```bash
ssh user@192.168.55.72
cd /path/to/labels_britannika
docker-compose ps
```

Ожидаемый результат:
```
britannica-backend    running
britannica-frontend   running
britannica-sync       running
```

### 2. Проверьте логи backend

```bash
docker-compose logs backend --tail 50
```

Ищите ошибки импорта или startup ошибки.

### 3. Проверьте что backend отвечает

```bash
curl http://localhost:8000/health
```

Должен вернуть: `{"status": "healthy", ...}`

## Решение

### Вариант 1: Обновить код и перезапустить

```bash
# 1. Обновить код
cd /path/to/labels_britannika
git pull origin main

# 2. Пересобрать backend (если изменились зависимости)
docker-compose build backend

# 3. Перезапустить все сервисы
docker-compose down
docker-compose up -d

# 4. Проверить логи
docker-compose logs -f backend
```

### Вариант 2: Если контейнеры не запущены

```bash
# Запустить с нуля
cd /path/to/labels_britannika
docker-compose up -d

# Проверить статус
docker-compose ps

# Если backend не стартует, проверить логи
docker-compose logs backend
```

### Вариант 3: Если база данных не инициализирована

```bash
# Зайти в контейнер backend
docker-compose exec backend bash

# Инициализировать БД
python scripts/init_db.py

# Выйти
exit

# Перезапустить
docker-compose restart backend
```

## Проверка после исправления

1. Откройте http://192.168.55.72:5000
2. Откройте DevTools (F12) → Network
3. Попробуйте войти с `admin/admin`
4. Проверьте что запрос к `/api/auth/login` возвращает 200 OK

## Недавние исправления

### Коммит e2d3945 (ОБЯЗАТЕЛЬНО применить!)
**FIX: Correct import of get_current_user in sync_api.py**

Исправлена критическая ошибка импорта в sync_api.py:
```python
# Было (неправильно):
from app.core.security import get_current_user

# Стало (правильно):
from app.api.auth_api import get_current_user
```

Без этого исправления логин не работает!

### Коммит f1821c2
**UPDATE: Upgrade dependencies for Python 3.13 compatibility**

Обновлены версии библиотек - требуется пересборка образа:
```bash
docker-compose build backend
docker-compose up -d
```

## Типичные ошибки

### 502 Bad Gateway
Backend не запущен или упал при старте.

**Решение:**
```bash
docker-compose logs backend
# Ищите Python traceback или import errors
```

### WebSocket connection failed
Frontend не может подключиться к WebSocket backend.

**Решение:**
1. Проверьте что backend запущен
2. Проверьте nginx конфигурацию (если используется)
3. Проверьте firewall правила

### Auth check failed: Unknown error
Backend запущен, но возвращает ошибку при `/api/auth/check`.

**Причина:** Обычно это ошибка импорта в коде (как в sync_api.py)

**Решение:**
1. `git pull origin main` - получить последние исправления
2. `docker-compose restart backend`

## Контакты

Если проблема не решается:
1. Соберите логи: `docker-compose logs > logs.txt`
2. Проверьте версию кода: `git log --oneline -5`
3. Сообщите в команду разработки
