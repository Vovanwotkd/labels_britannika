# 🏷️ Britannica Labels - Система Печати Этикеток для Ресторанов

Автономный сервис печати этикеток для ресторанов сети Britannica Project. Работает в локальной сети, обеспечивает прослеживаемость продукции согласно требованиям СанПиН и ГОСТ.

---

## 📋 Оглавление

- [Описание проекта](#описание-проекта)
- [Ключевые возможности](#ключевые-возможности)
- [Архитектура](#архитектура)
- [Технологический стек](#технологический-стек)
- [Требования](#требования)
- [Установка](#установка)
- [Конфигурация](#конфигурация)
- [Использование](#использование)
- [Разработка](#разработка)
- [Документация](#документация)

---

## 🎯 Описание проекта

**Britannica Labels** — это standalone веб-сервис, который:

1. **Принимает заказы** из RKeeper через XML webhook
2. **Обогащает данные** блюд из Store House 5 (БЖУ, вес, состав, дополнительные этикетки)
3. **Генерирует TSPL команды** для термопринтера PC-365B / XP-D365B
4. **Печатает этикетки** напрямую по TCP:9100 (без драйверов)
5. **Предоставляет UI** для операторов кухни (real-time доска заказов)

### Зачем это нужно?

- ✅ **Прослеживаемость** — каждая этикетка содержит состав, БЖУ, дату изготовления, срок годности
- ✅ **Автоматизация** — оператор видит заказы в реальном времени, печать одной кнопкой
- ✅ **Контроль качества** — раздельная упаковка соусов и добавок
- ✅ **Соответствие нормам** — СанПиН 2.3.2.1324-03, ГОСТ Р 51074-2003
- ✅ **Автономность** — работает в локальной сети, не зависит от интернета

---

## ✨ Ключевые возможности

### Для операторов кухни

- 📊 **Real-time доска заказов** — WebSocket обновления, цветовая индикация статусов
- 🖨️ **Быстрая печать** — весь заказ одной кнопкой, или точечная печать конкретного блюда
- 🔁 **Переотпечатка** — если этикетка повреждена или потеряна
- 🎨 **Цветовая индикация**:
  - 🟡 Новый заказ (NOT_PRINTED)
  - 🟦 В очереди (QUEUED)
  - 🟪 Печатается (PRINTING)
  - 🟢 Готово (DONE)
  - 🔴 Ошибка (FAILED) — с кнопкой повтора

### Для администраторов

- 🛠️ **Настройки**:
  - Принтер (IP, порт, тест печати)
  - Store House 5 (синхронизация данных блюд)
  - Фильтр столов (какие заказы отслеживать)
  - Параметры этикеток (размер бумаги, GAP, срок годности)

- 📝 **Шаблоны этикеток**:
  - Брендовые шаблоны для разных концепций
  - Настройка элементов (логотип, шрифты, штрих-коды)
  - Тест печати перед применением

- 👥 **Управление пользователями**:
  - Роли: `operator` (печать), `admin` (настройки)
  - Регистрация новых пользователей через UI

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────┐
│           RKeeper (кассовая система)                    │
│              XML Webhook Interface                      │
└────────────────────┬────────────────────────────────────┘
                     │ POST /api/webhook/rkeeper
                     ↓
┌─────────────────────────────────────────────────────────┐
│         Britannica Labels Service (мини-ПК)             │
│                                                          │
│  Backend (FastAPI + Python):                            │
│  ├─ Webhook receiver (RKeeper XML parser)               │
│  ├─ SQLite (заказы, шаблоны, пользователи)             │
│  ├─ dishes_with_extras.sqlite (создаётся локально)     │
│  ├─ TSPL renderer (Pillow, генерация команд)           │
│  ├─ TCP:9100 printer client                            │
│  └─ WebSocket server (real-time updates)               │
│                                                          │
│  Frontend (React + Vite):                               │
│  ├─ Доска заказов (WebSocket подписка)                 │
│  ├─ Редактор шаблонов                                   │
│  └─ Панель настроек                                     │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ↓                       ↓
┌──────────────────┐    ┌──────────────────┐
│  Операторы       │    │  Принтер         │
│  (планшет/ПК)    │    │  PC-365B         │
│  http://labels   │    │  TCP:9100        │
└──────────────────┘    │  203 dpi TSPL    │
                        └──────────────────┘

┌─────────────────────────────────────────────────────────┐
│         Store House 5 (управление товарами)             │
│              Синхронизация 1x/день                      │
│              export_dishes_with_extras.py               │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Технологический стек

### Backend
- **Python 3.11+** — язык программирования
- **FastAPI** — веб-фреймворк, REST API, WebSocket
- **SQLite** — база данных (заказы, шаблоны, пользователи)
- **SQLAlchemy** — ORM для работы с БД
- **Pillow** — генерация изображений для TSPL
- **aiohttp** — async HTTP клиент для Store House API
- **APScheduler** — фоновые задачи (синхронизация, архивация)
- **bcrypt** — хеширование паролей

### Frontend
- **React 18** — UI библиотека
- **TypeScript** — типизация
- **Vite** — build tool
- **Tailwind CSS** — стилизация
- **WebSocket API** — real-time обновления
- **react-router-dom** — навигация

### Deployment
- **Ubuntu/Debian** — операционная система (мини-ПК)
- **systemd** — автозапуск сервиса
- **nginx** — reverse proxy (опционально)

---

## 📦 Требования

### Hardware
- **Мини-ПК**: Intel NUC / Raspberry Pi 4 / аналог (2GB+ RAM)
- **Принтер**: PC-365B / Xprinter XP-D365B (203 dpi, TSPL/TSPL2)
- **Сеть**: LAN/Wi-Fi, статический IP или mDNS

### Software
- **ОС**: Ubuntu 20.04+ / Debian 11+
- **Python**: 3.11+
- **Node.js**: 18+ (для сборки frontend)
- **RKeeper**: XML Interface настроен на webhook
- **Store House 5**: API доступ (http://10.0.0.141:9797/api/sh5exec)

---

## 🚀 Установка

⚠️ **ВАЖНО:** Прочитайте [SECURITY.md](SECURITY.md) перед началом! Credentials не должны попадать в git.

### 1. Клонирование репозитория

```bash
git clone https://github.com/Vovanwotkd/-labels_britannika.git
cd -labels_britannika
```

### 1.1. Настройка credentials

```bash
# Создайте .env из примера
cp .env.example .env

# Укажите свои данные
nano .env
```

**Обязательно измените:**
- `SH5_URL`, `SH5_USER`, `SH5_PASS` - доступ к Store House 5
- `PRINTER_IP` - IP адрес вашего принтера
- `SECRET_KEY` - сгенерируйте новый ключ:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

### 1.2. Создайте скрипт экспорта

```bash
# Скопируйте пример
cp export_dishes_with_extras.py.example export_dishes_with_extras.py

# Отредактируйте (или используйте .env)
nano export_dishes_with_extras.py
```

### 2. Backend установка

```bash
cd backend

# Создание виртуального окружения
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Инициализация БД
python init_db.py

# Создание admin пользователя (admin/admin)
python create_admin.py
```

### 3. Frontend установка

```bash
cd frontend

# Установка зависимостей
npm install

# Production build
npm run build

# Файлы будут в frontend/dist/
```

### 4. Синхронизация Store House 5

```bash
# Разово
python export_dishes_with_extras.py

# Настройка cron (ежедневно в 3:00)
crontab -e
# Добавить: 0 3 * * * /path/to/venv/bin/python /path/to/export_dishes_with_extras.py
```

### 5. Запуск сервиса

```bash
# Development
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production (systemd)
sudo systemctl enable britannica-labels
sudo systemctl start britannica-labels
```

---

## ⚙️ Конфигурация

### Настройка принтера

1. Подключите PC-365B к сети (Wi-Fi или LAN)
2. Узнайте IP адрес принтера (например, 192.168.1.10)
3. Откройте `http://labels.local:8000/settings`
4. Укажите IP и порт 9100
5. Нажмите "Тест печати"

### Настройка RKeeper webhook

В RKeeper XML Interface добавьте подписку:

```xml
<Subscription>
  <Event name="SaveOrder"/>
  <URL>http://labels.local:8000/api/webhook/rkeeper</URL>
</Subscription>
```

### Настройка Store House 5

В веб-интерфейсе (`/settings`):
- URL: `http://10.0.0.141:9797/api/sh5exec`
- Логин: `Admin`
- Пароль: `******`
- Период синхронизации: `24 часа`

### Фильтр столов

1. Нажмите "Загрузить из RKeeper" (загружает справочник столов)
2. Выберите нужные столы (например, только Kitchen зона)
3. Сохраните

Теперь заказы с других столов не будут отображаться на доске.

---

## 📖 Использование

### Для операторов

1. Откройте `http://labels.local:8000` в браузере
2. Войдите (логин/пароль)
3. Увидите доску заказов

**Печать заказа:**
- Нажмите на карточку заказа
- Нажмите "Печать заказа" (печатает все блюда + доп. этикетки)

**Точечная печать:**
- Нажмите на карточку заказа
- Кликните на конкретное блюдо
- Нажмите "Печать"

**Переотпечатка:**
- Нажмите "Переотпечатать" на блюде
- Создаётся новая этикетка с новым временем

### Для администраторов

**Создание шаблона:**
1. Вкладка "Шаблоны"
2. Нажмите "+ Новый"
3. Настройте параметры (размер бумаги, срок годности, элементы)
4. Загрузите логотип (BMP 1-bit)
5. Сохраните
6. Нажмите "Тест печати"

**Добавление пользователя:**
1. Вкладка "Пользователи"
2. Нажмите "+ Добавить"
3. Укажите логин, пароль, роль
4. Сохраните

---

## 🔧 Разработка

### Структура проекта

```
britannica-labels/
├── backend/
│   ├── app/
│   │   ├── api/              # REST endpoints
│   │   │   ├── orders.py
│   │   │   ├── webhook.py
│   │   │   ├── templates.py
│   │   │   └── settings.py
│   │   ├── core/             # Конфигурация
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   ├── models/           # SQLAlchemy models
│   │   │   ├── order.py
│   │   │   ├── template.py
│   │   │   └── user.py
│   │   ├── services/         # Бизнес-логика
│   │   │   ├── printer.py    # TSPL renderer + TCP client
│   │   │   ├── queue.py      # Print queue worker
│   │   │   ├── sh5_sync.py   # Store House sync
│   │   │   └── rkeeper.py    # XML parser
│   │   └── schemas/          # Pydantic schemas
│   ├── main.py               # FastAPI app
│   ├── requirements.txt
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── OrderBoard/   # Доска заказов
│   │   │   ├── Templates/    # Редактор шаблонов
│   │   │   ├── Settings/     # Настройки
│   │   │   └── Users/        # Пользователи
│   │   ├── hooks/            # Custom hooks
│   │   ├── services/         # API client
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── export_dishes_with_extras.py   # Синхронизация SH5
├── dishes_with_extras.sqlite      # Мастер-база блюд (создаётся скриптом)
├── README.md
├── IMPLEMENTATION.md              # Детальный план разработки
└── .gitignore
```

**Примечание:** Файлы для изучения (`westpower.fiji/`, `XML (2)/`) не включены в репозиторий.
Они использовались для изучения интеграции с RKeeper и Bitrix, но не нужны для работы сервиса.

### Запуск в dev режиме

**Backend:**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
# Откроется http://localhost:5173
# Проксирует API запросы на localhost:8000
```

### Тестирование

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test
```

---

## 📚 Документация

- [IMPLEMENTATION.md](IMPLEMENTATION.md) — детальный план разработки (5 недель)
- [API.md](docs/API.md) — REST API спецификация
- [DATABASE.md](docs/DATABASE.md) — схема базы данных
- [TSPL.md](docs/TSPL.md) — формат TSPL команд, генерация этикеток
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) — инструкция по установке на production

---

## 📝 Changelog

### v1.0.0 (планируется)
- ✅ Приём заказов из RKeeper
- ✅ Доска заказов (real-time)
- ✅ Печать этикеток (основные + дополнительные)
- ✅ Шаблоны (настройка параметров)
- ✅ Авторизация (operator/admin)
- ✅ Настройки (принтер, StoreHouse, фильтр столов)

---

## 🤝 Вклад в проект

Проект разрабатывается для ресторанов сети Britannica Project.

---

## 📄 Лицензия

Proprietary — использование только для Britannica Project.

---

## 👥 Авторы

- **Разработка**: Britannica Project IT Team
- **Контакты**: it@britannica-project.com

---

## 🆘 Поддержка

**Проблемы с принтером:**
1. Проверьте сетевое подключение (ping IP принтера)
2. Убедитесь, что порт 9100 открыт
3. Попробуйте тест печати из настроек
4. Проверьте логи: `/var/log/britannica-labels/printer.log`

**Не приходят заказы:**
1. Проверьте настройку webhook в RKeeper
2. Проверьте фильтр столов (может стол не выбран)
3. Проверьте логи: `/var/log/britannica-labels/webhook.log`

**Нет данных блюд:**
1. Запустите синхронизацию Store House вручную
2. Проверьте доступность API Store House
3. Проверьте `dishes_with_extras.sqlite` (должен быть > 5MB)

---

**Версия документа**: 1.0
**Дата**: 19.10.2025
**Timezone**: GMT+2
