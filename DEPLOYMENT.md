# Britannica Labels - Deployment Guide

Руководство по развертыванию системы печати этикеток на Ubuntu/Debian.

## Требования

### Оборудование
- Мини-ПК (Ubuntu 20.04+ или Debian 11+)
- Принтер PC-365B / XP-D365B (TCP/IP)
- Сетевое подключение

### Программное обеспечение
- Docker 24.0+ и Docker Compose 2.0+
- (Опционально) Python 3.11+, Node.js 20+

## Вариант 1: Deployment с Docker (Рекомендуется)

### 1.1. Установка Docker

```bash
# Обновляем систему
sudo apt-get update
sudo apt-get upgrade -y

# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER

# Устанавливаем Docker Compose
sudo apt-get install docker-compose-plugin -y

# Проверяем установку
docker --version
docker compose version
```

### 1.2. Клонирование проекта

```bash
cd /opt
sudo git clone https://github.com/Vovanwotkd/labels_britannika.git
sudo chown -R $USER:$USER labels_britannika
cd labels_britannika
```

### 1.3. Конфигурация

```bash
# Копируем шаблон конфигурации
cp .env.example .env

# Редактируем конфигурацию
nano .env
```

**Обязательно укажите:**
- `SH5_PASS` - пароль Store House 5
- `SECRET_KEY` - секретный ключ (сгенерируйте: `python3 -c "import secrets; print(secrets.token_hex(32))"`)
- `PRINTER_IP` - IP адрес принтера

### 1.4. Подготовка dishes_with_extras.sqlite

```bash
# Создаём скрипт синхронизации из примера
cp backend/export_dishes_with_extras.py.example backend/export_dishes_with_extras.py

# Редактируем credentials
nano backend/export_dishes_with_extras.py

# Запускаем синхронизацию
cd backend
python3 export_dishes_with_extras.py
cd ..
```

### 1.5. Запуск приложения

```bash
# Сборка и запуск
docker compose up -d

# Проверка логов
docker compose logs -f

# Проверка статуса
docker compose ps
```

### 1.6. Проверка работоспособности

```bash
# Backend API
curl http://localhost:8000/health

# Frontend
curl http://localhost/

# Открываем в браузере
# http://<IP-адрес-мини-ПК>/
```

### 1.7. Управление сервисами

```bash
# Остановка
docker compose down

# Перезапуск
docker compose restart

# Обновление кода
git pull
docker compose build
docker compose up -d

# Просмотр логов
docker compose logs backend
docker compose logs frontend
```

## Вариант 2: Deployment без Docker

### 2.1. Установка зависимостей

```bash
# Python
sudo apt-get install python3.11 python3.11-venv python3-pip -y

# Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install nodejs -y

# Nginx
sudo apt-get install nginx -y
```

### 2.2. Backend Setup

```bash
cd backend

# Создаём virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt

# Копируем конфигурацию
cp ../backend/.env.example .env
nano .env

# Инициализируем БД
python scripts/init_db.py

# Синхронизируем блюда
cp export_dishes_with_extras.py.example export_dishes_with_extras.py
nano export_dishes_with_extras.py
python export_dishes_with_extras.py
```

### 2.3. Frontend Setup

```bash
cd frontend

# Устанавливаем зависимости
npm install

# Сборка production
npm run build
```

### 2.4. Systemd Service для Backend

Создайте файл `/etc/systemd/system/britannica-backend.service`:

```ini
[Unit]
Description=Britannica Labels Backend
After=network.target

[Service]
Type=simple
User=britannica
Group=britannica
WorkingDirectory=/opt/labels_britannika/backend
Environment="PATH=/opt/labels_britannika/backend/venv/bin"
ExecStart=/opt/labels_britannika/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Создаём пользователя
sudo useradd -r -s /bin/false britannica
sudo chown -R britannica:britannica /opt/labels_britannika

# Запускаем сервис
sudo systemctl daemon-reload
sudo systemctl enable britannica-backend
sudo systemctl start britannica-backend
sudo systemctl status britannica-backend
```

### 2.5. Nginx конфигурация

Создайте файл `/etc/nginx/sites-available/britannica-labels`:

```nginx
server {
    listen 80;
    server_name labels.local;

    # Frontend (статика)
    location / {
        root /opt/labels_britannika/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Логирование
    access_log /var/log/nginx/britannica-labels-access.log;
    error_log /var/log/nginx/britannica-labels-error.log;
}
```

```bash
# Активируем конфигурацию
sudo ln -s /etc/nginx/sites-available/britannica-labels /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Настройка автоматической синхронизации блюд

### Cron для синхронизации

```bash
# Редактируем crontab
crontab -e

# Добавляем задачу (каждый день в 3:00)
0 3 * * * cd /opt/labels_britannika/backend && /opt/labels_britannika/backend/venv/bin/python export_dishes_with_extras.py >> /var/log/britannica-sync.log 2>&1
```

## Настройка принтера

### Проверка доступности принтера

```bash
# Ping принтера
ping 192.168.1.10

# Проверка порта 9100
nc -zv 192.168.1.10 9100

# Тестовая печать через backend API
curl -X POST http://localhost:8000/api/print/test
```

## Мониторинг

### Логи

```bash
# Docker
docker compose logs -f backend
docker compose logs -f frontend

# Systemd
sudo journalctl -u britannica-backend -f

# Nginx
sudo tail -f /var/log/nginx/britannica-labels-access.log
sudo tail -f /var/log/nginx/britannica-labels-error.log
```

### Healthcheck

```bash
# Backend
curl http://localhost:8000/health

# Frontend
curl http://localhost/

# Принтер
curl http://localhost:8000/api/print/status
```

## Обновление

### Docker

```bash
cd /opt/labels_britannika
git pull
docker compose build
docker compose down
docker compose up -d
```

### Без Docker

```bash
cd /opt/labels_britannika

# Обновляем код
git pull

# Обновляем backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Обновляем frontend
cd ../frontend
npm install
npm run build

# Перезапускаем сервисы
sudo systemctl restart britannica-backend
sudo systemctl reload nginx
```

## Бэкапы

### Автоматический бэкап БД

```bash
#!/bin/bash
# /opt/britannica-backup.sh

BACKUP_DIR="/opt/backups/britannica"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Бэкап основной БД
cp /opt/labels_britannika/backend/data/britannica_labels.db $BACKUP_DIR/britannica_labels_$DATE.db

# Бэкап dishes DB
cp /opt/labels_britannika/backend/dishes_with_extras.sqlite $BACKUP_DIR/dishes_with_extras_$DATE.sqlite

# Удаляем бэкапы старше 30 дней
find $BACKUP_DIR -name "*.db" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
# Добавляем в crontab (каждый день в 4:00)
0 4 * * * /opt/britannica-backup.sh >> /var/log/britannica-backup.log 2>&1
```

## Troubleshooting

### Проблема: Backend не запускается

```bash
# Проверяем логи
docker compose logs backend
# или
sudo journalctl -u britannica-backend -n 100

# Проверяем .env
cat backend/.env

# Проверяем БД
ls -la backend/data/
```

### Проблема: Принтер не печатает

```bash
# Проверяем доступность
ping $PRINTER_IP
nc -zv $PRINTER_IP 9100

# Проверяем логи queue worker
docker compose logs backend | grep "Print queue worker"

# Тестовая печать
curl -X POST http://localhost:8000/api/print/test
```

### Проблема: WebSocket не подключается

```bash
# Проверяем nginx конфигурацию
sudo nginx -t

# Проверяем логи nginx
sudo tail -f /var/log/nginx/error.log

# Проверяем WebSocket в браузере (F12 → Network → WS)
```

## Безопасность

### Firewall

```bash
# Разрешаем только необходимые порты
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### SSL/TLS (опционально)

```bash
# Установка certbot
sudo apt-get install certbot python3-certbot-nginx -y

# Получение сертификата
sudo certbot --nginx -d labels.yourdomain.com
```

## Контакты и поддержка

- GitHub: https://github.com/Vovanwotkd/labels_britannika
- Issues: https://github.com/Vovanwotkd/labels_britannika/issues
