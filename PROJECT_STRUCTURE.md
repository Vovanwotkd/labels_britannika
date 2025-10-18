# Структура Проекта Britannica Labels

```
britannica-labels/
│
├── backend/                          # Backend (Python FastAPI)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI приложение (точка входа)
│   │   │
│   │   ├── api/                      # REST API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── orders.py            # /api/orders
│   │   │   ├── webhook.py           # /api/webhook/rkeeper
│   │   │   ├── print.py             # /api/print
│   │   │   ├── templates.py         # /api/templates
│   │   │   ├── settings.py          # /api/settings
│   │   │   ├── users.py             # /api/users
│   │   │   ├── auth.py              # /api/auth
│   │   │   └── websocket.py         # /ws
│   │   │
│   │   ├── core/                     # Конфигурация
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # Настройки (из .env)
│   │   │   ├── database.py          # SQLAlchemy setup
│   │   │   └── security.py          # Хеширование паролей, сессии
│   │   │
│   │   ├── models/                   # SQLAlchemy ORM модели
│   │   │   ├── __init__.py
│   │   │   ├── order.py             # Order, OrderItem, PrintJob
│   │   │   ├── template.py          # Template
│   │   │   ├── user.py              # User, Session
│   │   │   ├── settings.py          # Setting
│   │   │   └── table_filter.py      # TableFilter
│   │   │
│   │   ├── schemas/                  # Pydantic schemas (валидация)
│   │   │   ├── __init__.py
│   │   │   ├── order.py
│   │   │   ├── template.py
│   │   │   ├── user.py
│   │   │   └── settings.py
│   │   │
│   │   └── services/                 # Бизнес-логика
│   │       ├── __init__.py
│   │       │
│   │       ├── printer/              # Печать
│   │       │   ├── __init__.py
│   │       │   ├── tspl_renderer.py # TSPL генератор
│   │       │   ├── tcp_client.py    # TCP:9100 client
│   │       │   ├── queue_worker.py  # Async print queue
│   │       │   └── print_service.py # Высокоуровневый API
│   │       │
│   │       ├── rkeeper/              # RKeeper интеграция
│   │       │   ├── __init__.py
│   │       │   └── xml_parser.py    # XML webhook parser
│   │       │
│   │       ├── dishes/               # Блюда (Store House)
│   │       │   ├── __init__.py
│   │       │   └── dish_service.py  # Работа с dishes_with_extras.sqlite
│   │       │
│   │       └── orders/               # Заказы
│   │           ├── __init__.py
│   │           └── order_service.py # Создание заказов, print jobs
│   │
│   ├── alembic/                      # Database миграции
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── tests/                        # Тесты
│   │   ├── test_tspl_renderer.py
│   │   ├── test_printer_client.py
│   │   ├── test_order_service.py
│   │   └── test_api.py
│   │
│   ├── requirements.txt              # Python зависимости
│   ├── .env.example                  # Пример конфигурации
│   └── pytest.ini
│
├── frontend/                         # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── components/
│   │   │   ├── OrderBoard/          # Доска заказов
│   │   │   │   ├── OrderCard.tsx
│   │   │   │   ├── OrderFilters.tsx
│   │   │   │   └── OrderBoard.tsx
│   │   │   │
│   │   │   ├── Templates/           # Шаблоны
│   │   │   │   ├── TemplateList.tsx
│   │   │   │   ├── TemplateEditor.tsx
│   │   │   │   └── TemplatePreview.tsx
│   │   │   │
│   │   │   ├── Settings/            # Настройки
│   │   │   │   ├── Settings.tsx
│   │   │   │   ├── PrinterSettings.tsx
│   │   │   │   ├── SH5Settings.tsx
│   │   │   │   └── TableFilter.tsx
│   │   │   │
│   │   │   ├── Users/               # Пользователи
│   │   │   │   ├── UserList.tsx
│   │   │   │   └── UserForm.tsx
│   │   │   │
│   │   │   ├── Auth/                # Авторизация
│   │   │   │   └── LoginForm.tsx
│   │   │   │
│   │   │   └── Layout/              # Общие компоненты
│   │   │       ├── Navbar.tsx
│   │   │       └── Layout.tsx
│   │   │
│   │   ├── services/                # API клиенты
│   │   │   ├── api.ts               # REST API client
│   │   │   └── websocket.ts         # WebSocket client
│   │   │
│   │   ├── hooks/                   # Custom hooks
│   │   │   ├── useWebSocket.ts
│   │   │   └── useAuth.ts
│   │   │
│   │   ├── stores/                  # State management (Zustand)
│   │   │   ├── ordersStore.ts
│   │   │   ├── templatesStore.ts
│   │   │   └── authStore.ts
│   │   │
│   │   ├── types/                   # TypeScript типы
│   │   │   └── index.ts
│   │   │
│   │   ├── App.tsx                  # Main component
│   │   └── main.tsx                 # Entry point
│   │
│   ├── public/                      # Статические файлы
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
│
├── docs/                            # Документация
│   ├── API.md                       # REST API спецификация
│   ├── DATABASE.md                  # Схема базы данных
│   ├── TSPL.md                      # TSPL формат, примеры
│   └── DEPLOYMENT.md                # Инструкция по установке
│
├── scripts/                         # Утилиты и скрипты
│   ├── init_db.py                   # Инициализация БД
│   ├── create_admin.py              # Создание admin пользователя
│   ├── backup.sh                    # Backup скрипт
│   ├── britannica-labels.service    # systemd service
│   └── nginx.conf                   # nginx конфигурация
│
├── uploads/                         # Загруженные файлы (логотипы)
│   └── .gitkeep
│
├── print_queue/                     # Временные TSPL файлы
│   └── .gitkeep
│
├── backups/                         # Backup БД
│   └── .gitkeep
│
├── export_dishes_with_extras.py    # Синхронизация Store House 5
├── dishes_with_extras.sqlite       # Мастер-база блюд (26k записей)
│
├── .gitignore
├── README.md                        # Описание проекта
├── IMPLEMENTATION.md                # Детальный план разработки (5 недель)
└── PROJECT_STRUCTURE.md             # Этот файл
```

---

## Описание Ключевых Компонентов

### Backend

#### `app/main.py`
FastAPI приложение, регистрация роутеров, startup/shutdown события.

#### `app/api/`
REST API endpoints. Каждый файл — отдельный роутер (Blueprint).

#### `app/core/`
- `config.py` — настройки из .env (DATABASE_URL, PRINTER_IP, etc)
- `database.py` — SQLAlchemy engine, session, Base
- `security.py` — хеширование паролей, проверка сессий

#### `app/models/`
SQLAlchemy ORM модели (таблицы БД).

#### `app/schemas/`
Pydantic модели для валидации входных/выходных данных API.

#### `app/services/`
Бизнес-логика, разделённая по модулям:
- **printer/** — TSPL renderer, TCP client, print queue
- **rkeeper/** — парсинг XML от RKeeper
- **dishes/** — запросы к dishes_with_extras.sqlite
- **orders/** — создание заказов, генерация print jobs

---

### Frontend

#### `src/components/`
React компоненты, разделённые по функционалу.

#### `src/services/`
API клиенты (fetch, WebSocket).

#### `src/hooks/`
Custom hooks для переиспользования логики.

#### `src/stores/`
Zustand stores для глобального состояния.

#### `src/types/`
TypeScript интерфейсы/типы.

---

### Данные

#### `dishes_with_extras.sqlite`
Мастер-база блюд из Store House 5. Обновляется скриптом `export_dishes_with_extras.py`.

**Таблицы:**
- `dishes` — основные блюда (26,772 записей)
- `ingredients` — ингредиенты (69,818 записей)
- `dish_extra_labels` — связи доп. этикеток
- `extra_dish_ingredients` — ингредиенты доп. блюд

#### `backend/britannica.sqlite`
Рабочая база данных сервиса.

**Таблицы:**
- `orders` — заказы из RKeeper
- `order_items` — позиции заказов
- `print_jobs` — очередь печати
- `templates` — шаблоны этикеток
- `users` — пользователи
- `sessions` — активные сессии
- `settings` — настройки системы
- `table_filter` — фильтр столов

---

### Scripts

#### `init_db.py`
Создаёт таблицы, добавляет default шаблон, начальные настройки.

#### `create_admin.py`
Создаёт пользователя `admin/admin`.

#### `backup.sh`
Резервное копирование БД (cron: ежедневно в 2:00).

#### `britannica-labels.service`
systemd service для автозапуска.

#### `nginx.conf`
Reverse proxy для production (frontend + backend + WebSocket).

---

## Переменные Окружения (.env)

```bash
# Database
DATABASE_URL=sqlite:///./britannica.sqlite

# Принтер
PRINTER_IP=192.168.1.10
PRINTER_PORT=9100

# Store House 5
SH5_URL=http://10.0.0.141:9797/api/sh5exec
SH5_USER=Admin
SH5_PASS=776417

# Timezone
TZ=Europe/Kiev  # GMT+2

# Security
SECRET_KEY=your-secret-key-here
SESSION_LIFETIME_HOURS=8

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/britannica-labels/app.log
```

---

## Команды Разработки

### Backend

```bash
cd backend

# Установка зависимостей
pip install -r requirements.txt

# Инициализация БД
python scripts/init_db.py

# Запуск dev сервера
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Тесты
pytest
```

### Frontend

```bash
cd frontend

# Установка зависимостей
npm install

# Запуск dev сервера
npm run dev

# Production build
npm run build

# Тесты
npm run test
```

### Store House Sync

```bash
# Разовая синхронизация
python export_dishes_with_extras.py

# Cron (ежедневно в 3:00)
0 3 * * * /path/to/python /path/to/export_dishes_with_extras.py
```

---

## Production Deployment

```bash
# 1. Установка на мини-ПК
git clone https://github.com/yourorg/britannica-labels.git /opt/britannica-labels
cd /opt/britannica-labels

# 2. Backend setup
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
python scripts/create_admin.py

# 3. Frontend build
cd ../frontend
npm install
npm run build

# 4. systemd service
sudo cp scripts/britannica-labels.service /etc/systemd/system/
sudo systemctl enable britannica-labels
sudo systemctl start britannica-labels

# 5. nginx
sudo cp scripts/nginx.conf /etc/nginx/sites-available/britannica-labels
sudo ln -s /etc/nginx/sites-available/britannica-labels /etc/nginx/sites-enabled/
sudo systemctl reload nginx

# 6. Backup cron
sudo cp scripts/backup.sh /opt/britannica-labels/
sudo chmod +x /opt/britannica-labels/scripts/backup.sh
(crontab -l ; echo "0 2 * * * /opt/britannica-labels/scripts/backup.sh") | crontab -
```

---

**Версия**: 1.0
**Дата**: 19.10.2025
