# Установка Britannica Labels через Docker на Ubuntu

Пошаговая инструкция для развёртывания системы этикеток на Ubuntu сервере с использованием Docker.

## Требования

- Ubuntu 20.04 или новее
- Доступ по SSH с правами sudo
- VPN доступ к StoreHouse 5
- Доступ к принтеру в локальной сети
- Минимум 2GB RAM, 10GB свободного места

---

## Шаг 1: Установка Docker и Docker Compose

### 1.1. Подключитесь к серверу:

```bash
ssh user@your-server-ip
```

### 1.2. Обновите систему:

```bash
sudo apt update
sudo apt upgrade -y
```

### 1.3. Установите зависимости:

```bash
sudo apt install -y ca-certificates curl gnupg lsb-release git
```

### 1.4. Добавьте официальный GPG ключ Docker:

```bash
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
```

### 1.5. Добавьте Docker репозиторий:

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

### 1.6. Установите Docker:

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 1.7. Проверьте установку:

```bash
sudo docker --version
sudo docker compose version
```

Должно показать версии Docker (24.x+) и Docker Compose (2.x+).

### 1.8. Добавьте текущего пользователя в группу docker (опционально):

```bash
sudo usermod -aG docker $USER
```

**Важно:** После этой команды нужно выйти и заново зайти по SSH, чтобы изменения вступили в силу.

### 1.9. Запустите и включите Docker:

```bash
sudo systemctl start docker
sudo systemctl enable docker
```

---

## Шаг 2: Клонирование репозитория

### 2.1. Выберите директорию для установки:

```bash
cd /opt
```

### 2.2. Клонируйте репозиторий:

```bash
sudo git clone https://github.com/your-username/labels_britannika.git
```

**Замените** `your-username/labels_britannika` на URL вашего репозитория.

### 2.3. Перейдите в директорию:

```bash
cd labels_britannika
```

---

## Шаг 3: Настройка конфигурации

### 3.1. Создайте файл .env из примера:

```bash
sudo cp .env.example .env
```

### 3.2. Отредактируйте .env файл:

```bash
sudo nano .env
```

Заполните настоящие данные:

```bash
# ==============================================
# Britannica Labels - Environment Configuration
# ==============================================

# ПРИЛОЖЕНИЕ
APP_NAME=Britannica Labels
APP_VERSION=0.1.0
ENVIRONMENT=production

# TIMEZONE (Калининград GMT+2)
TZ=Europe/Kaliningrad
TIMEZONE=Europe/Kaliningrad

# БАЗА ДАННЫХ
DATABASE_URL=sqlite:///./data/britannica_labels.db

# ==============================================
# STOREHOUSE 5 (важно!)
# ==============================================
SH5_URL=http://10.0.0.141:9797/api/sh5exec
SH5_USER=Admin
SH5_PASS=YOUR_STOREHOUSE_PASSWORD_HERE

# ==============================================
# ПРИНТЕР (важно!)
# ==============================================
PRINTER_IP=192.168.1.10
PRINTER_PORT=9100
PRINTER_TIMEOUT=5

# ==============================================
# БЕЗОПАСНОСТЬ (важно!)
# ==============================================
# Сгенерируйте случайный ключ:
# python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=YOUR_GENERATED_SECRET_KEY_HERE

# ==============================================
# НАСТРОЙКИ
# ==============================================
DEFAULT_SHELF_LIFE_HOURS=6
```

**Важно заменить:**
- `SH5_PASS` - пароль от StoreHouse 5
- `PRINTER_IP` - IP адрес вашего принтера в сети
- `SECRET_KEY` - сгенерируйте случайный ключ (инструкция в комментарии)

**Для генерации SECRET_KEY:**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Скопируйте результат в `SECRET_KEY=...`

Сохраните файл: `Ctrl+O`, `Enter`, `Ctrl+X`

### 3.3. Создайте скрипт синхронизации:

```bash
sudo cp backend/export_dishes_with_extras.py.example backend/export_dishes_with_extras.py
sudo nano backend/export_dishes_with_extras.py
```

Отредактируйте credentials (строки 11-13):

```python
# StoreHouse 5 connection
SH_URL = "http://10.0.0.141:9797/api/sh5exec"
SH_USER = "Admin"
SH_PASS = "YOUR_STOREHOUSE_PASSWORD_HERE"  # ВАЖНО: Укажите реальный пароль!
```

Сохраните: `Ctrl+O`, `Enter`, `Ctrl+X`

---

## Шаг 4: Первая синхронизация (важно!)

**ВАЖНО:** Перед запуском Docker нужно один раз вручную синхронизировать блюда из StoreHouse.

### 4.1. Установите Python 3 (если нет):

```bash
sudo apt install -y python3 python3-pip
```

### 4.2. Установите зависимости:

```bash
cd backend
sudo pip3 install requests
```

### 4.3. Запустите первую синхронизацию:

```bash
sudo python3 export_dishes_with_extras.py
```

Должно появиться:

```
Connecting to StoreHouse 5...
Fetching dishes...
Processing 150 dishes...
Saved to dishes_with_extras.sqlite
✅ Sync completed successfully!
```

### 4.4. Проверьте что БД создана:

```bash
ls -lh dishes_with_extras.sqlite
```

Должен показать файл `dishes_with_extras.sqlite` размером 100-500KB.

### 4.5. Вернитесь в корень проекта:

```bash
cd ..
```

---

## Шаг 5: Выбор портов (важно!)

У вас на сервере уже есть Nginx и другие сервисы. Выберите один из вариантов:

### Вариант A: Отдельный порт (рекомендуется для теста)

Отредактируйте `docker-compose.yml`:

```bash
sudo nano docker-compose.yml
```

Найдите секцию `frontend` → `ports` и измените:

```yaml
ports:
  - "8090:80"  # Frontend будет доступен на порту 8090
```

Система будет доступна по адресу: `http://your-server-ip:8090`

### Вариант B: Интеграция с существующим Nginx (для production)

Оставьте `docker-compose.yml` без изменений (порт 80 не будет опубликован).

Вместо этого настройте reverse proxy в вашем основном Nginx:

```bash
sudo nano /etc/nginx/sites-available/britannica-labels
```

```nginx
server {
    listen 80;
    server_name labels.yourdomain.com;  # или используйте IP

    # Frontend (статические файлы)
    location /labels/ {
        proxy_pass http://localhost:8090/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /labels/api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /labels/ws/ {
        proxy_pass http://localhost:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 7d;
    }
}
```

Включите конфигурацию:

```bash
sudo ln -s /etc/nginx/sites-available/britannica-labels /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Для варианта B также нужно изменить `docker-compose.yml`:

```yaml
# В секции backend добавьте:
ports:
  - "8000:8000"

# В секции frontend измените:
ports:
  - "8090:80"
```

---

## Шаг 6: Запуск Docker контейнеров

### 6.1. Соберите образы:

```bash
sudo docker compose build
```

Это займёт 5-10 минут при первом запуске.

### 6.2. Запустите контейнеры:

```bash
sudo docker compose up -d
```

`-d` означает запуск в фоновом режиме (detached).

### 6.3. Проверьте статус контейнеров:

```bash
sudo docker compose ps
```

Должно показать 3 контейнера в статусе `running`:
- `britannica-backend`
- `britannica-frontend`
- `britannica-sync`

---

## Шаг 7: Проверка работоспособности

### 7.1. Проверьте логи backend:

```bash
sudo docker compose logs backend
```

Должно быть без ошибок, последняя строка: `Uvicorn running on http://0.0.0.0:8000`

### 7.2. Проверьте логи frontend:

```bash
sudo docker compose logs frontend
```

### 7.3. Проверьте логи sync:

```bash
sudo docker compose logs sync
```

Должно показать: `[timestamp] Starting dishes sync...` и `Sync completed. Next run in 24 hours.`

### 7.4. Проверьте API через curl:

```bash
curl http://localhost:8000/health
```

Должен вернуть: `{"status":"ok"}`

### 7.5. Откройте в браузере:

Если выбрали **Вариант A** (отдельный порт):
```
http://your-server-ip:8090
```

Если выбрали **Вариант B** (через существующий Nginx):
```
http://your-server-ip/labels/
```

Должна открыться страница входа Britannica Labels.

---

## Шаг 8: Настройка firewall

Если используете UFW (Ubuntu Firewall), откройте порты:

### Для варианта A (отдельный порт):

```bash
sudo ufw allow 8090/tcp
```

### Для варианта B (через Nginx):

```bash
# Если Nginx уже настроен, ничего дополнительно не нужно
# Убедитесь что порт 80 открыт:
sudo ufw allow 80/tcp
```

Проверьте статус:

```bash
sudo ufw status
```

---

## Шаг 9: Настройка RKeeper webhook

Теперь нужно настроить RKeeper для отправки заказов в систему.

### URL для webhook (в зависимости от выбранного варианта):

**Вариант A** (отдельный порт):
```
http://your-server-ip:8000/api/webhook/rkeeper
```

**Вариант B** (через Nginx):
```
http://your-server-ip/labels/api/webhook/rkeeper
```

### Настройка в RKeeper:

1. Откройте настройки RKeeper Manager
2. Найдите раздел "Webhooks" или "Внешние уведомления"
3. Добавьте новый webhook:
   - **URL:** (см. выше)
   - **Method:** POST
   - **Content-Type:** application/xml
   - **Events:** Order Created, Order Updated
4. Сохраните настройки

---

## Шаг 10: Тестирование

### 10.1. Войдите в систему:

- Логин: `admin`
- Пароль: `admin123`

**ВАЖНО:** Сразу после входа смените пароль в Settings!

### 10.2. Проверьте наличие блюд:

1. Откройте страницу "Печать этикеток"
2. Должны отображаться блюда из StoreHouse 5
3. Попробуйте найти любое блюдо через поиск

### 10.3. Проверьте принтер:

1. Откройте Settings → Printer
2. Проверьте что указан правильный IP
3. Нажмите "Test Connection"
4. Должно показать: "✅ Printer is reachable"

### 10.4. Напечатайте тестовую этикетку:

1. Выберите любое блюдо
2. Укажите дату производства, срок годности
3. Нажмите "Печать"
4. Проверьте что этикетка напечаталась

### 10.5. Проверьте webhook RKeeper:

1. Создайте заказ в RKeeper
2. Заказ должен автоматически появиться в Orders
3. Проверьте логи backend:

```bash
sudo docker compose logs backend | grep webhook
```

Должны быть записи о получении webhook от RKeeper.

---

## Управление системой

### Просмотр логов:

```bash
# Все логи реального времени
sudo docker compose logs -f

# Только backend
sudo docker compose logs -f backend

# Только sync (синхронизация)
sudo docker compose logs -f sync

# Последние 50 строк
sudo docker compose logs --tail 50
```

### Перезапуск контейнеров:

```bash
# Все
sudo docker compose restart

# Только backend
sudo docker compose restart backend

# Только sync
sudo docker compose restart sync
```

### Остановка системы:

```bash
sudo docker compose stop
```

### Запуск системы:

```bash
sudo docker compose start
```

### Полная остановка и удаление контейнеров:

```bash
sudo docker compose down
```

### Обновление системы:

```bash
# 1. Остановить контейнеры
sudo docker compose down

# 2. Обновить код
sudo git pull origin main

# 3. Пересобрать образы
sudo docker compose build

# 4. Запустить заново
sudo docker compose up -d
```

---

## Мониторинг синхронизации

### Проверить когда последний раз обновлялась БД блюд:

```bash
ls -lh backend/dishes_with_extras.sqlite
```

### Просмотреть логи синхронизации:

```bash
sudo docker compose logs sync
```

### Запустить синхронизацию вручную (без ожидания 24 часов):

```bash
sudo docker compose exec sync python export_dishes_with_extras.py
```

### Изменить периодичность синхронизации:

Отредактируйте `docker-compose.yml`:

```bash
sudo nano docker-compose.yml
```

Найдите `sleep 86400` в секции `sync` и замените:

- 1 час: `sleep 3600`
- 6 часов: `sleep 21600`
- 12 часов: `sleep 43200`
- 24 часа: `sleep 86400` (по умолчанию)

Перезапустите sync контейнер:

```bash
sudo docker compose restart sync
```

---

## Резервное копирование

### Создать резервную копию вручную:

```bash
# Создать директорию для бэкапов
sudo mkdir -p /opt/backups/britannica

# Копировать базы данных
sudo cp backend/data/britannica_labels.db /opt/backups/britannica/britannica_labels_$(date +%Y%m%d_%H%M%S).db
sudo cp backend/dishes_with_extras.sqlite /opt/backups/britannica/dishes_$(date +%Y%m%d_%H%M%S).sqlite
```

### Автоматические бэкапы через cron:

```bash
sudo crontab -e
```

Добавьте:

```cron
# Ежедневный бэкап в 4:00
0 4 * * * cp /opt/labels_britannika/backend/data/britannica_labels.db /opt/backups/britannica/britannica_labels_$(date +\%Y\%m\%d).db
```

---

## Troubleshooting

### Проблема: Контейнер не запускается

```bash
# Проверить логи
sudo docker compose logs

# Проверить что .env файл корректен
cat .env

# Пересоздать контейнеры
sudo docker compose up -d --force-recreate
```

### Проблема: Блюда не загружаются

```bash
# Проверить что dishes_with_extras.sqlite существует
ls -lh backend/dishes_with_extras.sqlite

# Проверить логи синхронизации
sudo docker compose logs sync

# Запустить синхронизацию вручную
sudo docker compose exec sync python export_dishes_with_extras.py
```

### Проблема: Не печатает на принтер

```bash
# Проверить доступность принтера с сервера
ping PRINTER_IP

# Проверить порт
telnet PRINTER_IP 9100

# Проверить логи backend
sudo docker compose logs backend | grep printer
```

### Проблема: RKeeper webhook не работает

```bash
# Проверить что backend доступен снаружи
curl http://YOUR_SERVER_IP:8000/health

# Проверить firewall
sudo ufw status

# Проверить логи webhook
sudo docker compose logs backend | grep webhook
```

### Проблема: Недостаточно места на диске

```bash
# Очистить старые Docker образы
sudo docker system prune -a

# Удалить старые логи
sudo docker compose logs --tail 0
```

---

## Безопасность

### Смена пароля администратора:

1. Войдите как `admin`
2. Settings → Security → Change Password
3. Установите надёжный пароль

### Настройка HTTPS (рекомендуется для production):

Если у вас есть доменное имя, используйте Let's Encrypt:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d labels.yourdomain.com
```

Certbot автоматически настроит SSL для вашего Nginx.

---

## Системные требования

**Минимальные:**
- CPU: 2 cores
- RAM: 2GB
- Disk: 10GB

**Рекомендуемые:**
- CPU: 4 cores
- RAM: 4GB
- Disk: 20GB
- SSD диск для лучшей производительности

---

## Полезные команды

```bash
# Статистика использования ресурсов контейнерами
sudo docker stats

# Информация о системе Docker
sudo docker info

# Список всех контейнеров
sudo docker ps -a

# Список образов
sudo docker images

# Очистка неиспользуемых ресурсов
sudo docker system prune

# Посмотреть IP адреса контейнеров
sudo docker network inspect britannica-network
```

---

## Контакты и поддержка

- **Документация:** README.md, DEPLOYMENT.md, SYNC.md
- **Безопасность:** SECURITY.md
- **Issues:** GitHub Issues

---

**Готово! 🚀**

Система Britannica Labels успешно развёрнута через Docker и готова к использованию!
