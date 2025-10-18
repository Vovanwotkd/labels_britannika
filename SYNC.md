# Автоматическая синхронизация блюд со StoreHouse 5

Инструкция по настройке автоматической синхронизации данных блюд из StoreHouse 5.

## Как это работает

Скрипт `export_dishes_with_extras.py` загружает из StoreHouse 5:
- Все блюда с составом
- БЖУ (белки, жиры, углеводы)
- Калории
- Вес
- Дополнительные этикетки (AddListSauce)

И сохраняет в `dishes_with_extras.sqlite` - это мастер-база блюд.

## Варианты автоматической синхронизации

### 🐳 Вариант 1: Docker Compose (Рекомендуется)

**Периодичность:** Каждые 24 часа автоматически

#### Настройка:

1. Создайте скрипт синхронизации:
```bash
cd backend
cp export_dishes_with_extras.py.example export_dishes_with_extras.py
```

2. Отредактируйте credentials в `export_dishes_with_extras.py`:
```python
SH_URL = "http://10.0.0.141:9797/api/sh5exec"
SH_USER = "Admin"
SH_PASS = "ваш_пароль"
```

3. Запустите все сервисы (включая sync):
```bash
docker compose up -d
```

Теперь у вас запущены 3 контейнера:
- `britannica-backend` - основной backend
- `britannica-frontend` - frontend
- `britannica-sync` - синхронизация (каждые 24 часа)

#### Просмотр логов синхронизации:

```bash
# Логи sync контейнера
docker compose logs -f sync

# Последняя синхронизация
docker compose logs sync --tail 50
```

#### Изменение периодичности:

В `docker-compose.yml` измените `sleep 86400` (секунды):
- 1 час: `sleep 3600`
- 6 часов: `sleep 21600`
- 12 часов: `sleep 43200`
- 24 часа: `sleep 86400` (по умолчанию)

```yaml
command: >
  sh -c "while true; do
    echo '[$(date)] Starting dishes sync...'
    python export_dishes_with_extras.py || echo 'Sync failed'
    echo '[$(date)] Sync completed. Next run in 24 hours.'
    sleep 86400  # <-- Здесь
  done"
```

Затем перезапустите:
```bash
docker compose restart sync
```

#### Ручной запуск синхронизации:

```bash
# Запустить синхронизацию сейчас
docker compose exec sync python export_dishes_with_extras.py

# Перезапустить sync контейнер (начнёт цикл заново)
docker compose restart sync
```

---

### 🖥️ Вариант 2: Cron (для установки без Docker)

**Периодичность:** Настраивается через crontab

#### Настройка:

1. Создайте скрипт синхронизации:
```bash
cd /opt/labels_britannika/backend
sudo -u britannica cp export_dishes_with_extras.py.example export_dishes_with_extras.py
sudo nano export_dishes_with_extras.py
```

2. Отредактируйте credentials

3. Создайте wrapper скрипт:
```bash
sudo nano /opt/britannica-sync.sh
```

```bash
#!/bin/bash
# Britannica Labels - Sync Script

cd /opt/labels_britannika/backend
source venv/bin/activate
python export_dishes_with_extras.py
echo "[$(date)] Sync completed"
```

```bash
sudo chmod +x /opt/britannica-sync.sh
```

4. Настройте cron:
```bash
sudo crontab -e
```

Добавьте:
```cron
# Синхронизация каждый день в 3:00
0 3 * * * /opt/britannica-sync.sh >> /var/log/britannica-sync.log 2>&1

# Или каждые 12 часов (в 3:00 и 15:00)
0 3,15 * * * /opt/britannica-sync.sh >> /var/log/britannica-sync.log 2>&1

# Или каждые 6 часов
0 */6 * * * /opt/britannica-sync.sh >> /var/log/britannica-sync.log 2>&1
```

#### Просмотр логов:

```bash
tail -f /var/log/britannica-sync.log
```

#### Ручной запуск:

```bash
sudo /opt/britannica-sync.sh
```

---

### 💻 Вариант 3: Windows Task Scheduler

**Периодичность:** Настраивается в Task Scheduler

#### Настройка:

1. Создайте `sync.bat`:
```batch
@echo off
cd C:\Users\vovan\labels_britannika\backend
call venv\Scripts\activate
python export_dishes_with_extras.py
echo [%date% %time%] Sync completed >> sync.log
```

2. Откройте Task Scheduler (Планировщик заданий)

3. Create Basic Task:
   - Name: Britannica Sync
   - Trigger: Daily at 3:00 AM
   - Action: Start a program
   - Program: `C:\Users\vovan\labels_britannika\backend\sync.bat`

4. Настройки задачи:
   - ✅ Run whether user is logged on or not
   - ✅ Run with highest privileges
   - Trigger: Repeat every 12 hours (опционально)

#### Просмотр логов:

```powershell
type C:\Users\vovan\labels_britannika\backend\sync.log
```

---

## Проверка синхронизации

### Проверить когда последний раз обновлялась БД:

```bash
# Linux/Mac
ls -lh backend/dishes_with_extras.sqlite

# Windows
dir backend\dishes_with_extras.sqlite
```

### Проверить количество блюд:

```bash
# Linux/Mac
sqlite3 backend/dishes_with_extras.sqlite "SELECT COUNT(*) FROM dishes;"

# Windows (установи sqlite3)
sqlite3 backend\dishes_with_extras.sqlite "SELECT COUNT(*) FROM dishes;"
```

### Проверить через API:

```bash
curl http://localhost:8000/api/settings/system/info
```

В ответе будет:
```json
{
  "database": {
    "order_items": 123,
    ...
  }
}
```

---

## Первый запуск (важно!)

### Docker:

```bash
# 1. Первая ручная синхронизация ПЕРЕД запуском
cd backend
cp export_dishes_with_extras.py.example export_dishes_with_extras.py
nano export_dishes_with_extras.py
python export_dishes_with_extras.py

# Должен появиться dishes_with_extras.sqlite

# 2. Теперь запускаем Docker
cd ..
docker compose up -d

# Sync контейнер будет обновлять БД каждые 24 часа
```

### Без Docker:

```bash
# 1. Первая синхронизация
cd /opt/labels_britannika/backend
sudo -u britannica python export_dishes_with_extras.py

# 2. Настроить cron (см. выше)

# 3. Запустить backend
sudo systemctl start britannica-backend
```

---

## Мониторинг синхронизации

### Docker:

```bash
# Статус sync контейнера
docker compose ps sync

# Логи реального времени
docker compose logs -f sync

# История синхронизаций
docker compose logs sync | grep "Sync completed"
```

### Systemd + Cron:

```bash
# Логи cron
sudo tail -f /var/log/britannica-sync.log

# История синхронизаций
grep "Sync completed" /var/log/britannica-sync.log
```

---

## Troubleshooting

### Синхронизация падает с ошибкой

```bash
# Проверить доступность StoreHouse
ping 10.0.0.141
curl http://10.0.0.141:9797/api/sh5exec

# Проверить credentials в export_dishes_with_extras.py
# Проверить VPN (если используется)
```

### Sync контейнер не запускается (Docker)

```bash
# Проверить логи
docker compose logs sync

# Проверить что скрипт существует
ls -la backend/export_dishes_with_extras.py

# Пересоздать контейнер
docker compose up -d --force-recreate sync
```

### Устаревшие данные

```bash
# Проверить последнее обновление файла
stat backend/dishes_with_extras.sqlite

# Запустить синхронизацию вручную
docker compose exec sync python export_dishes_with_extras.py
# или
sudo /opt/britannica-sync.sh
```

---

## Рекомендуемая периодичность

- **Разработка/тест:** Вручную, по необходимости
- **Production (небольшое меню):** 1 раз в день (ночью)
- **Production (частые изменения):** 2 раза в день (ночь + обед)
- **Production (очень частые изменения):** Каждые 6 часов

**Не рекомендуется чаще 1 раза в час** - это нагрузка на StoreHouse и не нужно для этикеток.

---

## Альтернатива: Ручная синхронизация через UI (будущая фича)

В будущем можно добавить кнопку в UI (Settings):
- "Синхронизировать блюда сейчас"
- Показывать дату последней синхронизации
- Показывать количество блюд в БД

Для реализации нужно:
1. Добавить API endpoint в backend
2. Добавить кнопку в Settings Page (frontend)
3. Запускать скрипт через subprocess

---

**Рекомендация:** Используйте Docker вариант - это проще всего! 🚀
