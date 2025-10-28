# Britannica Labels - Quick Start Guide

**Быстрое развертывание системы печати этикеток (30-60 минут)**

> Подробная инструкция: [INSTALL.md](INSTALL.md) и [DEPLOYMENT.md](DEPLOYMENT.md)

---

## ✅ Checklist развертывания

### 1️⃣ Подготовка сервера (5 минут)

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Клонирование проекта
cd /opt
sudo git clone https://github.com/Vovanwotkd/labels_britannika.git
sudo chown -R $USER:$USER labels_britannika
cd labels_britannika
```

**✓ Проверка:** `docker --version` должен показать версию 24.0+

---

### 2️⃣ Настройка CUPS + Принтер (15 минут)

```bash
# Установка CUPS
sudo apt update
sudo apt install cups

# Установка драйвера XPrinter
sudo dpkg -i printer-driver-xprinter_3.13.3_all.deb
sudo apt-get install -f

# Настройка доступа из Docker
sudo nano /etc/cups/cupsd.conf
```

Добавить в `/etc/cups/cupsd.conf`:
```
Port 631

<Location />
  Order allow,deny
  Allow localhost
  Allow 172.17.0.0/16  # Docker network
</Location>
```

```bash
# Перезапуск CUPS
sudo systemctl restart cups
```

**Добавление принтера через веб-интерфейс:**
1. Открыть `http://localhost:631`
2. Administration → Add Printer
3. Выбрать сетевой принтер (TCP/IP)
4. Адрес: `192.168.X.X` (IP вашего принтера)
5. Драйвер: **XPrinter XP-365B**
6. Настроить параметры (58x60mm, Darkness: 10)

**✓ Проверка:** `lpstat -p` должен показать принтер в состоянии "idle"

---

### 3️⃣ Конфигурация проекта (5 минут)

```bash
cd /opt/labels_britannika

# Создание .env файла
cp .env.example .env
nano .env
```

**Минимальная конфигурация `.env`:**
```bash
# StoreHouse 5 (обязательно)
SH5_URL=http://10.0.0.141:9797/api/sh5exec
SH5_USER=Admin
SH5_PASS=your_password_here

# Безопасность (обязательно)
SECRET_KEY=$(openssl rand -hex 32)

# Принтер (если используете TCP вместо CUPS)
PRINTER_IP=192.168.1.10
PRINTER_PORT=9100

# Опционально
DEFAULT_SHELF_LIFE_HOURS=6
TIMEZONE=Europe/Kaliningrad
DEBUG_SAVE_PNG=false
```

**✓ Проверка:** `cat .env | grep SH5_PASS` должен показать ваш пароль

---

### 4️⃣ Первый запуск (5 минут)

```bash
cd /opt/labels_britannika

# Сборка и запуск
sudo docker compose up -d --build

# Проверка статуса
sudo docker compose ps
sudo docker compose logs backend --tail 50
```

**✓ Проверка:** Все сервисы должны быть "Up" и "healthy"

**Доступ:**
- Frontend: `http://localhost:5000`
- Backend API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

---

### 5️⃣ Синхронизация данных из StoreHouse (10 минут)

```bash
# Первая синхронизация (вручную)
sudo docker compose exec backend python export_dishes_full.py
```

Эта команда:
- ✅ Подключится к StoreHouse 5
- ✅ Выгрузит все блюда с иерархией подразделений
- ✅ Создаст файл `dishes_full.sqlite`
- ✅ Займёт 5-10 минут в зависимости от количества блюд

**Автоматическая синхронизация:**
- Настроена через sync container (каждые 24 часа)
- Можно запустить вручную через UI: Настройки → Синхронизация

**✓ Проверка:**
```bash
ls -lh /opt/labels_britannika/dishes_full.sqlite
# Должен быть файл размером ~500KB - 5MB
```

---

### 6️⃣ Настройка RKeeper webhook (10 минут)

**В RKeeper Manager:**

1. Откройте настройки событий (Event Manager)
2. Создайте новый event:
   - **Тип:** HTTP POST
   - **URL:** `http://<IP_СЕРВЕРА>:8000/api/webhook/rkeeper`
   - **События:**
     - ✅ Save Order
     - ✅ Quit Order
   - **Формат:** XML

3. Сохраните и активируйте

**Тестирование webhook:**
```bash
# Смотрим логи
sudo docker compose logs backend -f

# Создайте тестовый заказ в RKeeper и сохраните
# В логах должны появиться сообщения:
# "📨 RKeeper event: Save Order"
# "✅ Webhook processed: order_id=..."
```

**✓ Проверка:** В UI (`http://localhost:5000`) должен появиться новый заказ

---

### 7️⃣ Финальная настройка через UI (10 минут)

1. **Авторизация:**
   - Откройте `http://localhost:5000`
   - Логин: `admin` / Пароль: `admin`
   - Смените пароль: Настройки → Пользователи

2. **Настройка принтера:**
   - Настройки → Принтер
   - Выберите режим: **CUPS** (рекомендуется) или **TCP**
   - Укажите имя принтера: `XPrinter` (из CUPS)
   - Darkness: `10` (яркость печати)

3. **Фильтр подразделений:**
   - Настройки → Фильтры
   - Выберите подразделения для печати (дерево)
   - Сохраните

4. **Шаблон этикетки:**
   - Шаблоны → Редактировать шаблон
   - Настройте расположение элементов
   - Сохраните

**✓ Проверка:**
- Создайте тестовый заказ в RKeeper
- Он должен появиться в UI со статусом "Новый" (синий)
- Этикетки должны напечататься автоматически
- Статус заказа должен стать "Готово" (зелёный)

---

## 🎯 Что должно работать после настройки:

✅ **RKeeper → Backend:**
- Webhook отправляется при сохранении заказа
- Заказ создаётся в системе автоматически
- Игнорируются промежуточные события (Order Changed)

✅ **Backend → Принтер:**
- Этикетки генерируются автоматически (по количеству порций)
- Печать через CUPS с PNG рендерингом
- Дополнительные этикетки для блюд с компонентами

✅ **UI Updates:**
- Real-time обновления через WebSocket
- Статусы: Новый → Печатается → Готово
- Возможность переиспользования заказов

✅ **Фильтрация:**
- Печать только блюд из выбранных подразделений
- Каскадная фильтрация (родитель → дети)

✅ **Синхронизация:**
- Автоматическая синхронизация каждую минуту (fallback)
- Ручная синхронизация через кнопку "Обновить"
- Экспорт блюд из StoreHouse (каждые 24 часа)

---

## 🔧 Troubleshooting

### Заказы не появляются в UI
```bash
# Проверить webhook события
sudo docker compose logs backend --tail 100 | grep "RKeeper event"

# Проверить фильтры (Save Order / Quit Order)
sudo docker compose logs backend | grep "Skipping event"

# Принудительная синхронизация
curl -X POST http://localhost:8000/api/sync/orders
```

### Этикетки не печатаются
```bash
# Проверить статус принтера
lpstat -p

# Проверить CUPS
systemctl status cups

# Проверить печать вручную
lp -d XPrinter test.png

# Проверить логи печати
sudo docker compose logs backend | grep "print\|CUPS"
```

### Блюда не найдены в базе
```bash
# Пересинхронизировать StoreHouse
sudo docker compose exec backend python export_dishes_full.py

# Проверить размер БД
ls -lh /opt/labels_britannika/dishes_full.sqlite

# Проверить содержимое
sqlite3 dishes_full.sqlite "SELECT COUNT(*) FROM dishes;"
```

### DEBUG режим
```bash
# Включить сохранение PNG
nano .env
# DEBUG_SAVE_PNG=true

sudo docker compose up -d --build

# PNG будут сохраняться в:
ls -lh /opt/labels_britannika/backend/data/debug_labels/
```

---

## 📚 Дополнительные ресурсы

- **Полная инструкция:** [INSTALL.md](INSTALL.md) - детальная настройка CUPS, принтера, миграции
- **Deployment guide:** [DEPLOYMENT.md](DEPLOYMENT.md) - развертывание на production
- **API документация:** `http://localhost:8000/docs` - Swagger UI
- **Diagnostic commands:** [DIAGNOSTIC_COMMANDS.md](DIAGNOSTIC_COMMANDS.md) - команды для диагностики

---

## 💡 Рекомендации

1. **Бэкап:** Регулярно бэкапьте `/opt/labels_britannika/backend/data/britannica_labels.db`
2. **Мониторинг:** Проверяйте логи раз в день: `sudo docker compose logs --tail 100`
3. **Обновления:** `git pull && sudo docker compose up -d --build`
4. **Безопасность:** Смените пароль admin и SECRET_KEY в production

---

## ⏱️ Итоговое время развертывания:

- ⚡ Минимальная установка (без CUPS): **20 минут**
- 🎯 Полная установка (с CUPS + настройка): **45-60 минут**
- 🚀 Повторное развертывание (есть backup конфигов): **10 минут**

---

**Готово!** Система должна работать полностью автоматически:
RKeeper → Webhook → Backend → Принтер → Этикетки ✅

При возникновении проблем смотрите логи:
```bash
sudo docker compose logs backend -f
```
