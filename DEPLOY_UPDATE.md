# 🚀 Быстрое обновление на сервере

## Команды для обновления после git push

Выполните на сервере **192.168.55.72**:

```bash
# 1. Перейти в директорию проекта
cd ~/labels_britannika

# 2. Получить последние изменения
git pull origin main

# 3. Пересобрать backend образ
sudo docker compose build backend

# 4. Перезапустить сервисы
sudo docker compose down
sudo docker compose up -d

# 5. Проверить статус
sudo docker compose ps

# 6. Посмотреть логи (опционально)
sudo docker compose logs -f backend
```

## Быстрая команда (всё в одну строку)

```bash
cd ~/labels_britannika && git pull origin main && sudo docker compose build backend && sudo docker compose down && sudo docker compose up -d
```

## Проверка после обновления

1. Откройте http://192.168.55.72:5000
2. Войдите с `admin` / `admin`
3. Перейдите в **Настройки**
4. Нажмите **"Проверить связь"** для каждого сервиса:
   - ✅ Принтер
   - ✅ StoreHouse 5
   - ✅ RKeeper

## Если что-то не работает

### Проблема: Backend не запускается

```bash
# Смотрим логи
sudo docker compose logs backend --tail 100

# Ищем:
# - ImportError (проблемы с импортами)
# - ModuleNotFoundError (не установлены зависимости)
# - Traceback (ошибки Python)
```

### Проблема: 502 Bad Gateway

Backend не отвечает. Проверьте:

```bash
# 1. Запущен ли контейнер?
sudo docker compose ps

# 2. Логи backend
sudo docker compose logs backend

# 3. Перезапустить backend
sudo docker compose restart backend
```

### Проблема: "Unknown error" при входе

Старый образ Docker. Нужна пересборка:

```bash
sudo docker compose build backend --no-cache
sudo docker compose up -d
```

## Откат к предыдущей версии

Если новая версия сломалась:

```bash
# 1. Откатить git
git log --oneline -5  # Посмотреть коммиты
git reset --hard <HASH_ПРЕДЫДУЩЕГО_КОММИТА>

# 2. Пересобрать
sudo docker compose build backend
sudo docker compose up -d
```

## История обновлений

### 2025-10-20 23:55

**Коммит d1209fd:** FIX: Disable SSL verification for self-signed certificates
- ✅ Исправлена ошибка подключения к StoreHouse 5 через HTTPS
- ✅ Добавлен `ssl=False` для самоподписанных сертификатов

**Коммит bda4260:** DOCS: Add troubleshooting guide
- 📚 Добавлен TROUBLESHOOTING.md

**Коммит f1821c2:** UPDATE: Upgrade dependencies for Python 3.13
- 📦 Обновлены зависимости (aiohttp, httpx, Pillow)

**Коммит e2d3945:** FIX: Correct import of get_current_user
- 🔧 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ импорта в sync_api.py
- ✅ Исправлена ошибка "Unknown error" при входе

**Коммит 9c38f34:** FEAT: StoreHouse sync now reads from database
- ⚙️ Sync теперь читает настройки из БД
- 🎨 Добавлена кнопка ручной синхронизации в UI

---

**Версия**: 1.1
**Последнее обновление**: 2025-10-20
