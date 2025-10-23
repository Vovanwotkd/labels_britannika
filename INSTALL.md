# Britannica Labels - Инструкция по установке

## Содержание

1. [Установка CUPS на сервере](#установка-cups-на-сервере)
2. [Установка драйвера принтера XPrinter](#установка-драйвера-принтера)
3. [Настройка принтера в CUPS](#настройка-принтера-в-cups)
4. [Настройка Docker контейнера](#настройка-docker-контейнера)
5. [Миграция базы данных](#миграция-базы-данных)
6. [Настройка через UI](#настройка-через-ui)
7. [Тестирование](#тестирование)
8. [Troubleshooting](#troubleshooting)

---

## Установка CUPS на сервере

CUPS (Common Unix Printing System) устанавливается **на хост-сервере** (не в Docker контейнере).

### Ubuntu/Debian

```bash
# Обновить список пакетов
sudo apt update

# Установить CUPS
sudo apt install cups

# Проверить статус
sudo systemctl status cups

# Если не запущен - запустить
sudo systemctl start cups
sudo systemctl enable cups
```

### Разрешить доступ к CUPS извне

По умолчанию CUPS доступен только на localhost. Для доступа из Docker контейнера:

```bash
# Редактировать конфиг
sudo nano /etc/cups/cupsd.conf
```

Найти секции и изменить:

```
# Allow remote access
Port 631

<Location />
  Order allow,deny
  Allow localhost
  Allow 172.17.0.0/16   # Docker bridge network
</Location>

<Location /admin>
  Order allow,deny
  Allow localhost
  Allow 172.17.0.0/16
</Location>
```

Перезапустить CUPS:

```bash
sudo systemctl restart cups
```

### Веб-интерфейс CUPS

Доступен по адресу: `http://localhost:631`

---

## Установка драйвера принтера

### Драйвер XPrinter (официальный .deb)

Драйвер уже находится в репозитории: `backend/drivers/printer-driver-xprinter_3.13.3_all.deb`

```bash
cd /путь/к/проекту

# Установить драйвер
sudo dpkg -i backend/drivers/printer-driver-xprinter_3.13.3_all.deb

# Если есть зависимости
sudo apt --fix-broken install

# Проверить установку
lpinfo -m | grep -i xprinter
```

Должны увидеть список поддерживаемых моделей:
```
xprinter:0/ppd/xprinter/XP-365B.ppd XPrinter XP-365B
xprinter:0/ppd/xprinter/XP-420B.ppd XPrinter XP-420B
...
```

---

## Настройка принтера в CUPS

### Через веб-интерфейс (рекомендуется)

1. Открыть `http://localhost:631`
2. Administration → Add Printer
3. Выбрать принтер:
   - **AppSocket/HP JetDirect** - для сетевого принтера
   - **USB Printer** - для USB подключения
4. Для сетевого принтера указать:
   - Connection: `socket://10.55.3.254:9100`
   - Name: `XPrinter` (или любое имя)
   - Location: `Kitchen` (опционально)
   - Share: ✅ (если нужен доступ из сети)
5. Выбрать драйвер:
   - Make: **XPrinter**
   - Model: **XP-365B** (или вашу модель)
6. Set Default Options:
   - Paper Size: **Custom.58x60mm** (или 58x40mm)
   - Print Quality: **Normal**
7. Нажать **Add Printer**

### Через командную строку

```bash
# Добавить принтер
sudo lpadmin -p XPrinter \
  -v socket://10.55.3.254:9100 \
  -m xprinter:0/ppd/xprinter/XP-365B.ppd \
  -L "Kitchen" \
  -E

# Установить размер бумаги
sudo lpadmin -p XPrinter -o media=Custom.58x60mm

# Включить принтер
sudo cupsenable XPrinter
sudo cupsaccept XPrinter
```

### Проверка

```bash
# Список принтеров
lpstat -p

# Должно быть:
# printer XPrinter is idle. enabled since ...

# Тестовая печать
echo "Test label" | lp -d XPrinter
```

---

## Настройка Docker контейнера

### Пересборка образа

После изменений в `Dockerfile` (добавлен `cups-client`):

```bash
cd /путь/к/проекту

# Остановить контейнер
docker-compose down

# Пересобрать образ
docker-compose build backend

# Запустить
docker-compose up -d
```

### Проверка cups-client в контейнере

```bash
# Войти в контейнер
docker exec -it britannika-backend bash

# Проверить доступность lp команды
which lp
# Вывод: /usr/bin/lp

# Проверить доступность CUPS на хосте
lpstat -h host.docker.internal -p

# Должен показать список принтеров с хоста
```

---

## Миграция базы данных

После установки CUPS нужно добавить новые настройки в БД:

```bash
cd /путь/к/проекту

# Войти в контейнер backend
docker exec -it britannika-backend bash

# Запустить миграцию
python backend/scripts/migrate_printer_settings.py
```

Вывод должен быть:
```
🔄 Начало миграции printer settings...
✅ Миграция выполнена успешно!
   Добавлено:
   - printer_type = 'tcp'
   - printer_name = ''

   Существующие настройки (printer_ip, printer_port) сохранены
```

### Что добавляет миграция

В таблицу `settings` добавляются:

| key | value | description |
|-----|-------|-------------|
| `printer_type` | `tcp` | Тип подключения: 'tcp' (raw TSPL) или 'cups' (драйвер) |
| `printer_name` | `""` | Имя CUPS принтера (используется только если printer_type=cups) |

---

## Настройка через UI

### Открыть Settings

1. Зайти в UI: `http://labels.local` (или IP сервера)
2. Login → Settings
3. Секция **Printer Settings**

### Выбрать режим CUPS

1. **Printer Type**:
   - `TCP (Raw TSPL)` - старый режим, прямая отправка TSPL команд
   - `CUPS (Driver)` - **новый режим**, печать через драйвер

2. Если выбран **CUPS**:
   - **Printer Name**: выбрать из dropdown списка доступных CUPS принтеров
   - Список загружается автоматически через API: `/api/printers/list`

3. **Save Settings**

### Настройки для TCP режима (legacy)

Если остаётся TCP режим:
- **Printer IP**: `10.55.3.254`
- **Printer Port**: `9100`

---

## Тестирование

### 1. Проверить API endpoint

```bash
# Список CUPS принтеров
curl -X GET http://localhost:8000/api/printers/list \
  -H "Authorization: Bearer YOUR_TOKEN"

# Ответ:
{
  "printers": [
    {
      "name": "XPrinter",
      "online": true,
      "status": "idle"
    }
  ],
  "count": 1
}
```

### 2. Создать тестовый заказ

1. Отправить webhook от RKeeper
2. Проверить в UI → Orders что заказ создан
3. Проверить что PrintJob создан со статусом QUEUED

### 3. Проверить логи печати

```bash
# Логи backend контейнера
docker logs -f britannika-backend

# Должно быть:
# 📄 Обработка job #123 (order_item_id=456)
# 📝 Используем CUPS принтер: XPrinter
# 🎨 Генерируем PNG для блюда: Лепешка с говядиной
# ✅ PNG сгенерирован: 25600 bytes (25.0 KB)
# ✅ Job #123 напечатан успешно
```

### 4. Проверить очередь CUPS

```bash
# На хосте
lpstat -o

# Если есть задания в очереди:
# XPrinter-12            user         1024   Wed 23 Oct 2025 12:34:56 PM
```

### 5. Физическая печать

Проверить что принтер физически напечатал этикетку с:
- Названием блюда (кириллица должна работать!)
- БЖУ
- Весом
- Составом
- Сроком годности

---

## Troubleshooting

### Проблема: "CUPS printer name not configured"

**Причина:** В настройках не указано имя CUPS принтера

**Решение:**
1. Зайти в Settings UI
2. Выбрать Printer Type = CUPS
3. Выбрать принтер из dropdown
4. Save Settings

### Проблема: "No CUPS printers found"

**Причина:** CUPS не видит принтер

**Диагностика:**
```bash
# На хосте проверить
lpstat -p

# Если принтера нет - добавить через lpadmin (см. выше)
```

### Проблема: "Connection refused to host.docker.internal:631"

**Причина:** CUPS не разрешает удалённые подключения

**Решение:**
1. Редактировать `/etc/cups/cupsd.conf`
2. Добавить Docker сеть в Allow (см. раздел установки)
3. Перезапустить CUPS: `sudo systemctl restart cups`

### Проблема: Печатаются полосы вместо текста

**Причина:** Вы используете TCP режим с битым BITMAP форматом

**Решение:**
Переключитесь на CUPS режим! Это именно для этого и было сделано - чтобы не мучиться с ручным TSPL.

### Проблема: Принтер печатает, но размер этикетки неправильный

**Причина:** Неправильный размер бумаги в CUPS

**Решение:**
```bash
# Установить размер
sudo lpadmin -p XPrinter -o media=Custom.58x60mm

# Или через веб-интерфейс CUPS:
# Administration → Manage Printers → XPrinter → Set Default Options
```

### Проблема: Кириллица не печатается

**Причина:** Отсутствует шрифт DejaVuSans.ttf

**Решение:**
```bash
# В контейнере
docker exec -it britannika-backend bash
ls /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf

# Если нет - уже должен быть установлен через Dockerfile (fonts-dejavu-core)
```

### Проблема: "lpstat: command not found" в контейнере

**Причина:** cups-client не установлен

**Решение:**
1. Проверить Dockerfile - должна быть строка `cups-client` в apt-get install
2. Пересобрать образ: `docker-compose build backend`

### Логи для диагностики

```bash
# Backend логи
docker logs -f britannika-backend

# CUPS логи на хосте
tail -f /var/log/cups/error_log
tail -f /var/log/cups/access_log

# Print queue worker статус
# В UI → System Info → Jobs → queued/printing/failed
```

---

## Переключение между TCP и CUPS

Можно в любой момент переключаться между режимами через UI Settings:

### TCP режим (legacy)
- Использует raw TSPL команды
- Отправка напрямую на IP:Port принтера
- **Проблема:** кириллица может не работать (BITMAP баги)

### CUPS режим (рекомендуется)
- Использует официальный драйвер
- Генерирует PNG этикетки
- Печатает через CUPS на хосте
- **Преимущества:**
  - Универсальность
  - Кириллица работает идеально
  - Не нужно знать TSPL

---

## Дополнительно

### Несколько принтеров

Можно настроить несколько принтеров в CUPS и переключаться между ними через UI:

```bash
# Добавить второй принтер
sudo lpadmin -p XPrinter-Kitchen \
  -v socket://10.55.3.254:9100 \
  -m xprinter:0/ppd/xprinter/XP-365B.ppd

sudo lpadmin -p XPrinter-Bar \
  -v socket://10.55.3.2:9100 \
  -m xprinter:0/ppd/xprinter/XP-365B.ppd
```

В UI dropdown покажет оба принтера для выбора.

### Автозапуск CUPS

```bash
sudo systemctl enable cups
```

Теперь CUPS будет стартовать при загрузке сервера.

---

**Готово!** После этих шагов система будет печатать этикетки через CUPS драйвер вместо ручных TSPL команд.
