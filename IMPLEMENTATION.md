# 📋 План Разработки Britannica Labels

**Версия**: 1.0
**Дата**: 19.10.2025
**Срок выполнения**: 5 недель
**Timezone**: GMT+2
**Язык интерфейса**: Русский

---

## 🎯 Цель MVP

Создать полнофункциональный сервис печати этикеток для ресторанов с возможностью:
- Приёма заказов из RKeeper
- Автоматической печати этикеток (основные + дополнительные)
- Real-time мониторинга заказов
- Управления шаблонами и настройками

---

## 📅 График Разработки

| Неделя | Компонент | Задачи | Статус |
|--------|-----------|--------|--------|
| **1** | Backend Core + Печать | Database ORM, TSPL Renderer, TCP Client, Print Queue | 🔄 |
| **2** | RKeeper Integration + Orders | Webhook Handler, Orders API, WebSocket Server | ⏳ |
| **3** | Frontend Orders Board | React UI, WebSocket Client, Доска заказов | ⏳ |
| **4** | Settings + Templates + Users | Настройки UI, Шаблоны CRUD, Управление пользователями | ⏳ |
| **5** | Deployment + Testing | systemd, nginx, тестирование на production | ⏳ |

---

## 📦 Неделя 1: Backend Core + Печать

### Цель
Базовая печать работает — можно напечатать этикетку по RK коду через API.

### Задачи

#### 1.1 Инициализация проекта ✅ (День 1)

**Структура папок:**
```
britannica-labels/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── requirements.txt
│   ├── .env.example
│   └── tests/
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── docs/
├── scripts/
├── .gitignore
├── README.md
└── IMPLEMENTATION.md
```

**requirements.txt:**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
aiohttp==3.9.1
pillow==10.1.0
apscheduler==3.10.4
websockets==12.0
```

**Файлы:**
- `backend/app/main.py` — FastAPI приложение
- `backend/app/core/config.py` — настройки (из .env)
- `backend/app/core/database.py` — SQLAlchemy setup
- `backend/.env.example` — пример конфигурации

---

#### 1.2 Database Schema (ORM) 🔄 (День 1-2)

**Модели (backend/app/models/):**

**orders.py:**
```python
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text
from sqlalchemy.sql import func
from app.core.database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(String, nullable=False, index=True)
    order_ident = Column(String, nullable=False, index=True)
    table_code = Column(String, nullable=False, index=True)
    order_total = Column(Numeric(10, 2))
    status = Column(String, nullable=False, default="NOT_PRINTED")  # NOT_PRINTED, QUEUED, PRINTING, DONE, FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('visit_id', 'order_ident', name='uix_visit_order'),
    )

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    rk_code = Column(String, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    dish_name = Column(String)
    weight_g = Column(Integer)
    printed_count = Column(Integer, default=0)
    last_printed_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", back_populates="items")

class PrintJob(Base):
    __tablename__ = "print_jobs"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=True)
    label_type = Column(String, nullable=False)  # MAIN, EXTRA
    dish_rid = Column(Integer)
    tspl_data = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="QUEUED")  # QUEUED, PRINTING, DONE, FAILED
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    printed_at = Column(DateTime(timezone=True), nullable=True)
```

**templates.py:**
```python
class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    brand_id = Column(String, unique=True)
    is_default = Column(Boolean, default=False)
    config = Column(JSON, nullable=False)  # JSON конфигурация
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**users.py:**
```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # operator, admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**settings.py:**
```python
class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text)
    description = Column(Text)
```

**table_filter.py:**
```python
class TableFilter(Base):
    __tablename__ = "table_filter"

    table_code = Column(String, primary_key=True)
    table_name = Column(String)
    zone = Column(String)
    enabled = Column(Boolean, default=True)
```

**Миграции:**
```bash
alembic init alembic
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

**Bootstrap данные:**
```python
# scripts/init_db.py
# Создаёт admin пользователя, default шаблон, начальные настройки
```

---

#### 1.3 TSPL Renderer ⏳ (День 2-3)

**backend/app/services/printer/tspl_renderer.py:**

```python
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from typing import Dict, Any
import io

class TSPLRenderer:
    def __init__(self, template_config: Dict[str, Any]):
        self.config = template_config
        self.dpi = 203  # PC-365B = 203 dpi
        self.mm_to_dots = 8  # 203 dpi ≈ 8 dots/mm

    def render(self, dish_data: Dict[str, Any]) -> str:
        """
        Генерирует TSPL команды для печати этикетки

        Args:
            dish_data: {
                "name": "Лепешка с говядиной",
                "rk_code": "2538",
                "weight_g": 259,
                "calories": 380,
                "protein": 25,
                "fat": 15,
                "carbs": 40,
                "ingredients": ["говядина", "тесто", "лук"],
                "label_type": "MAIN" | "EXTRA"
            }

        Returns:
            TSPL команды (str)
        """

        # Параметры из настроек
        width_mm = int(self.config.get("paper_width_mm", 60))
        height_mm = int(self.config.get("paper_height_mm", 60))
        gap_mm = int(self.config.get("paper_gap_mm", 2))
        shelf_life_hours = int(self.config.get("shelf_life_hours", 6))

        # Даты
        now = datetime.now()
        shelf_life = now + timedelta(hours=shelf_life_hours)

        # TSPL команды
        tspl = []

        # Заголовок
        tspl.append(f"SIZE {width_mm} mm, {height_mm} mm")
        tspl.append(f"GAP {gap_mm} mm, 0 mm")
        tspl.append("DIRECTION 1")
        tspl.append("CLS")

        # Логотип (если есть)
        if self.config.get("logo", {}).get("enabled"):
            logo_path = self.config["logo"]["path"]
            x = self.config["logo"]["x"]
            y = self.config["logo"]["y"]
            # BITMAP команда (нужен BMP 1-bit)
            # tspl.append(f'BITMAP {x},{y},"{logo_path}"')

        # Название блюда
        title_font = self.config.get("title", {}).get("font", "3")
        title_x = self.config.get("title", {}).get("x", 10)
        title_y = self.config.get("title", {}).get("y", 30)
        tspl.append(f'TEXT {title_x},{title_y},"{title_font}",0,1,1,"{dish_data["name"]}"')

        # Вес и калории
        wc_font = self.config.get("weight_calories", {}).get("font", "2")
        wc_x = self.config.get("weight_calories", {}).get("x", 10)
        wc_y = self.config.get("weight_calories", {}).get("y", 60)
        wc_text = f'Вес: {dish_data["weight_g"]}г | {dish_data["calories"]} ккал'
        tspl.append(f'TEXT {wc_x},{wc_y},"{wc_font}",0,1,1,"{wc_text}"')

        # БЖУ (если включено)
        if self.config.get("bju", {}).get("enabled", True):
            bju_font = self.config["bju"]["font"]
            bju_x = self.config["bju"]["x"]
            bju_y = self.config["bju"]["y"]
            bju_text = f'Б:{dish_data["protein"]}г Ж:{dish_data["fat"]}г У:{dish_data["carbs"]}г'
            tspl.append(f'TEXT {bju_x},{bju_y},"{bju_font}",0,1,1,"{bju_text}"')

        # Состав (если включено)
        if self.config.get("ingredients", {}).get("enabled", True) and dish_data.get("ingredients"):
            ing_font = self.config["ingredients"]["font"]
            ing_x = self.config["ingredients"]["x"]
            ing_y = self.config["ingredients"]["y"]
            max_lines = self.config["ingredients"].get("max_lines", 3)

            # Объединяем ингредиенты
            ingredients_str = ", ".join(dish_data["ingredients"][:max_lines])
            if len(dish_data["ingredients"]) > max_lines:
                ingredients_str += "..."

            tspl.append(f'TEXT {ing_x},{ing_y},"{ing_font}",0,1,1,"Состав: {ingredients_str}"')

        # Дата печати и срок годности
        dt_font = self.config.get("datetime_shelf", {}).get("font", "2")
        dt_x = self.config.get("datetime_shelf", {}).get("x", 10)
        dt_y = self.config.get("datetime_shelf", {}).get("y", 140)

        date_str = now.strftime("%d.%m %H:%M")
        shelf_str = shelf_life.strftime("%d.%m %H:%M")

        tspl.append(f'TEXT {dt_x},{dt_y},"{dt_font}",0,1,1,"Изготовлено: {date_str}"')
        tspl.append(f'TEXT {dt_x},{dt_y+20},"{dt_font}",0,1,1,"Годен до: {shelf_str}"')

        # Штрих-код
        bc_type = self.config.get("barcode", {}).get("type", "128")
        bc_x = self.config.get("barcode", {}).get("x", 10)
        bc_y = self.config.get("barcode", {}).get("y", 170)
        bc_height = self.config.get("barcode", {}).get("height", 50)
        bc_narrow = self.config.get("barcode", {}).get("narrow_bar", 2)

        tspl.append(f'BARCODE {bc_x},{bc_y},"{bc_type}",{bc_height},1,0,{bc_narrow},{bc_narrow},"{dish_data["rk_code"]}"')

        # Печать
        tspl.append("PRINT 1")

        return "\n".join(tspl)
```

**Тесты:**
```bash
pytest backend/tests/test_tspl_renderer.py
```

---

#### 1.4 TCP:9100 Printer Client ⏳ (День 3)

**backend/app/services/printer/tcp_client.py:**

```python
import socket
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class PrinterClient:
    def __init__(self, host: str, port: int = 9100, timeout: int = 5):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, tspl_data: str) -> bool:
        """
        Отправляет TSPL команды на принтер

        Returns:
            True если успешно, False если ошибка
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
                sock.sendall(tspl_data.encode('utf-8'))
                logger.info(f"Sent {len(tspl_data)} bytes to {self.host}:{self.port}")
                return True
        except socket.timeout:
            logger.error(f"Timeout connecting to printer {self.host}:{self.port}")
            return False
        except ConnectionRefusedError:
            logger.error(f"Connection refused to printer {self.host}:{self.port}")
            return False
        except Exception as e:
            logger.error(f"Error sending to printer: {e}")
            return False

    def test_connection(self) -> bool:
        """Проверяет доступность принтера"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
                return True
        except:
            return False
```

---

#### 1.5 Print Queue Worker ⏳ (День 4-5)

**backend/app/services/printer/queue_worker.py:**

```python
import asyncio
import logging
from sqlalchemy.orm import Session
from app.models.orders import PrintJob
from app.services.printer.tcp_client import PrinterClient
from app.core.database import SessionLocal
from app.core.config import settings

logger = logging.getLogger(__name__)

class PrintQueueWorker:
    def __init__(self):
        self.running = False
        self.printer = PrinterClient(
            host=settings.PRINTER_IP,
            port=settings.PRINTER_PORT
        )

    async def start(self):
        """Запускает worker"""
        self.running = True
        logger.info("Print queue worker started")

        while self.running:
            await self.process_queue()
            await asyncio.sleep(1)  # Проверка каждую секунду

    async def process_queue(self):
        """Обрабатывает очередь печати"""
        db: Session = SessionLocal()

        try:
            # Получаем jobs в статусе QUEUED
            jobs = db.query(PrintJob).filter(
                PrintJob.status == "QUEUED"
            ).order_by(PrintJob.created_at).limit(10).all()

            for job in jobs:
                await self.process_job(db, job)

        finally:
            db.close()

    async def process_job(self, db: Session, job: PrintJob):
        """Обрабатывает один job"""
        try:
            # Обновляем статус
            job.status = "PRINTING"
            db.commit()

            # Отправляем на принтер
            success = self.printer.send(job.tspl_data)

            if success:
                job.status = "DONE"
                job.printed_at = datetime.now()
                logger.info(f"Job {job.id} printed successfully")
            else:
                # Ретрай
                job.retry_count += 1

                if job.retry_count >= job.max_retries:
                    job.status = "FAILED"
                    job.error_message = "Max retries exceeded"
                    logger.error(f"Job {job.id} failed after {job.max_retries} retries")
                else:
                    job.status = "QUEUED"
                    logger.warning(f"Job {job.id} retry {job.retry_count}/{job.max_retries}")
                    await asyncio.sleep(5)  # Задержка перед ретраем

            db.commit()

        except Exception as e:
            logger.error(f"Error processing job {job.id}: {e}")
            job.status = "FAILED"
            job.error_message = str(e)
            db.commit()

    async def stop(self):
        """Останавливает worker"""
        self.running = False
        logger.info("Print queue worker stopped")
```

**Интеграция в main.py:**
```python
@app.on_event("startup")
async def startup():
    # Запускаем print queue worker
    worker = PrintQueueWorker()
    asyncio.create_task(worker.start())
```

---

#### 1.6 API Endpoints (базовые) ⏳ (День 5)

**backend/app/api/print.py:**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.print import PrintDishRequest
from app.services.printer.print_service import PrintService

router = APIRouter(prefix="/api/print", tags=["print"])

@router.post("/dish")
async def print_dish(request: PrintDishRequest, db: Session = Depends(get_db)):
    """
    Печать этикетки по RK коду

    Body:
        {
            "rk_code": "2538",
            "quantity": 1
        }
    """
    service = PrintService(db)
    result = await service.print_by_rk_code(request.rk_code, request.quantity)
    return result

@router.post("/test")
async def test_print(db: Session = Depends(get_db)):
    """Тестовая печать"""
    service = PrintService(db)
    result = await service.test_print()
    return result
```

---

### Результат Недели 1

✅ **Готово:**
- SQLite база данных с таблицами
- ORM модели (SQLAlchemy)
- TSPL renderer (генерация команд)
- TCP:9100 client
- Print queue worker (async, ретраи)
- API endpoint для тестовой печати

✅ **Можно протестировать:**
```bash
curl -X POST http://localhost:8000/api/print/dish \
  -H "Content-Type: application/json" \
  -d '{"rk_code": "2538", "quantity": 1}'
```

**Ожидаемый результат:** этикетка напечатана на принтере PC-365B

---

## 📦 Неделя 2: RKeeper Integration + Orders API

### Цель
Заказы из RKeeper попадают в систему, создаются записи в БД, генерируются print jobs.

### Задачи

#### 2.1 RKeeper Webhook Handler ⏳ (День 6-7)

**backend/app/services/rkeeper/xml_parser.py:**

```python
from xml.etree import ElementTree as ET
from typing import Dict, List, Optional

class RKeeperXMLParser:
    @staticmethod
    def parse_order_webhook(xml_data: str) -> Optional[Dict]:
        """
        Парсит XML от RKeeper webhook

        Пример:
        <a name="Save Order">
          <Order visit="12345" orderIdent="67890">
            <Table code="141"/>
            <ChangeLog>
              <Dish code="2538" quantity="1" uni="123"/>
              <Dish code="1055" quantity="2" uni="124"/>
            </ChangeLog>
          </Order>
        </a>

        Returns:
            {
                "action": "Save Order",
                "visit_id": "12345",
                "order_ident": "67890",
                "table_code": "141",
                "items": [
                    {"rk_code": "2538", "quantity": 1, "uni": "123"},
                    {"rk_code": "1055", "quantity": 2, "uni": "124"}
                ]
            }
        """
        try:
            root = ET.fromstring(xml_data)

            action_elem = root.find(".//a")
            action = action_elem.get("name")

            order_elem = root.find(".//Order")
            visit_id = order_elem.get("visit")
            order_ident = order_elem.get("orderIdent")

            table_elem = root.find(".//Table")
            table_code = table_elem.get("code")

            items = []
            changelog = root.find(".//ChangeLog")
            if changelog:
                for dish in changelog.findall("Dish"):
                    items.append({
                        "rk_code": dish.get("code"),
                        "quantity": int(dish.get("quantity", 1)),
                        "uni": dish.get("uni")
                    })

            return {
                "action": action,
                "visit_id": visit_id,
                "order_ident": order_ident,
                "table_code": table_code,
                "items": items
            }
        except Exception as e:
            logger.error(f"Error parsing RKeeper XML: {e}")
            return None
```

**backend/app/api/webhook.py:**

```python
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.rkeeper.xml_parser import RKeeperXMLParser
from app.services.orders.order_service import OrderService

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

@router.post("/rkeeper")
async def rkeeper_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Приём webhook от RKeeper
    """
    # Получаем raw XML
    xml_data = await request.body()
    xml_str = xml_data.decode('utf-8')

    # Логируем (опционально)
    logger.info(f"Received RKeeper webhook: {xml_str}")

    # Парсим
    parser = RKeeperXMLParser()
    parsed = parser.parse_order_webhook(xml_str)

    if not parsed:
        return {"status": "error", "message": "Invalid XML"}

    # Обрабатываем заказ
    service = OrderService(db)
    result = await service.process_rkeeper_order(parsed)

    return {"status": "ok", "order_id": result.id}
```

---

#### 2.2 Интеграция с dishes_with_extras.sqlite ⏳ (День 7-8)

**backend/app/services/dishes/dish_service.py:**

```python
import sqlite3
from typing import Dict, List, Optional

class DishService:
    def __init__(self, db_path: str = "dishes_with_extras.sqlite"):
        self.db_path = db_path

    def get_by_rk_code(self, rk_code: str) -> Optional[Dict]:
        """
        Получает блюдо по RK коду

        Returns:
            {
                "rid": 14376,
                "name": "Лепешка с говядиной",
                "rkeeper_code": "2538",
                "weight_g": 259,
                "protein": 25,
                "fat": 15,
                "carbs": 40,
                "calories": 380,
                "ingredients": ["говядина", "тесто", "лук"],
                "has_extra_labels": True,
                "extra_labels": [
                    {"rid": 7676, "name": "Соус", "weight_g": 565, ...},
                    {"rid": 8080, "name": "Гарнир", "weight_g": 310, ...}
                ]
            }
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Основное блюдо
        cursor.execute("""
            SELECT * FROM dishes WHERE rkeeper_code = ?
        """, (rk_code,))

        dish_row = cursor.fetchone()
        if not dish_row:
            return None

        dish = dict(dish_row)

        # Ингредиенты
        cursor.execute("""
            SELECT name FROM ingredients WHERE dish_rid = ?
        """, (dish['rid'],))

        dish['ingredients'] = [row['name'] for row in cursor.fetchall()]

        # Дополнительные этикетки
        dish['extra_labels'] = []
        if dish.get('has_extra_labels'):
            cursor.execute("""
                SELECT
                    extra_dish_rid,
                    extra_dish_name,
                    extra_dish_weight_g,
                    extra_dish_protein,
                    extra_dish_fat,
                    extra_dish_carbs,
                    extra_dish_calories
                FROM dish_extra_labels
                WHERE main_dish_rid = ?
                ORDER BY sort_order
            """, (dish['rid'],))

            dish['extra_labels'] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return dish
```

---

#### 2.3 Order Service (создание заказов) ⏳ (День 8-9)

**backend/app/services/orders/order_service.py:**

```python
from app.models.orders import Order, OrderItem, PrintJob
from app.services.dishes.dish_service import DishService
from app.services.printer.tspl_renderer import TSPLRenderer

class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.dish_service = DishService()

    async def process_rkeeper_order(self, parsed_data: Dict) -> Order:
        """
        Обрабатывает заказ от RKeeper

        1. Проверяет фильтр столов
        2. Создаёт/обновляет Order
        3. Создаёт OrderItems
        4. Генерирует PrintJobs (основные + доп. этикетки)
        """

        # 1. Проверка фильтра столов
        table_code = parsed_data['table_code']
        if not self._is_table_enabled(table_code):
            logger.info(f"Table {table_code} is not in filter, skipping")
            return None

        # 2. Создание/обновление заказа
        order = self.db.query(Order).filter(
            Order.visit_id == parsed_data['visit_id'],
            Order.order_ident == parsed_data['order_ident']
        ).first()

        if not order:
            order = Order(
                visit_id=parsed_data['visit_id'],
                order_ident=parsed_data['order_ident'],
                table_code=table_code,
                status='NOT_PRINTED'
            )
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)

        # 3. Создание позиций
        for item_data in parsed_data['items']:
            # Получаем данные блюда из dishes_with_extras.sqlite
            dish = self.dish_service.get_by_rk_code(item_data['rk_code'])

            if not dish:
                logger.warning(f"Dish not found: {item_data['rk_code']}")
                continue

            # Создаём OrderItem
            order_item = OrderItem(
                order_id=order.id,
                rk_code=item_data['rk_code'],
                quantity=item_data['quantity'],
                dish_name=dish['name'],
                weight_g=dish['weight_g']
            )
            self.db.add(order_item)
            self.db.commit()
            self.db.refresh(order_item)

            # Генерируем print jobs
            await self._create_print_jobs(order, order_item, dish)

        return order

    async def _create_print_jobs(self, order: Order, item: OrderItem, dish: Dict):
        """Создаёт print jobs для блюда"""

        # Получаем шаблон (пока default)
        template = self._get_default_template()
        renderer = TSPLRenderer(template.config)

        # Основная этикетка
        for i in range(item.quantity):
            tspl_data = renderer.render({
                "name": dish['name'],
                "rk_code": dish['rkeeper_code'],
                "weight_g": dish['weight_g'],
                "calories": dish['calories'],
                "protein": dish['protein'],
                "fat": dish['fat'],
                "carbs": dish['carbs'],
                "ingredients": dish['ingredients'],
                "label_type": "MAIN"
            })

            job = PrintJob(
                order_id=order.id,
                order_item_id=item.id,
                label_type='MAIN',
                dish_rid=dish['rid'],
                tspl_data=tspl_data,
                status='QUEUED'
            )
            self.db.add(job)

        # Дополнительные этикетки
        for extra in dish.get('extra_labels', []):
            for i in range(item.quantity):
                tspl_data = renderer.render({
                    "name": extra['extra_dish_name'],
                    "rk_code": dish['rkeeper_code'],  # Используем код основного блюда
                    "weight_g": extra['extra_dish_weight_g'],
                    "calories": extra['extra_dish_calories'],
                    "protein": extra['extra_dish_protein'],
                    "fat": extra['extra_dish_fat'],
                    "carbs": extra['extra_dish_carbs'],
                    "ingredients": [],  # Доп. этикетки без состава (упрощённые)
                    "label_type": "EXTRA"
                })

                job = PrintJob(
                    order_id=order.id,
                    order_item_id=item.id,
                    label_type='EXTRA',
                    dish_rid=extra['extra_dish_rid'],
                    tspl_data=tspl_data,
                    status='QUEUED'
                )
                self.db.add(job)

        self.db.commit()
```

---

#### 2.4 Orders API ⏳ (День 9)

**backend/app/api/orders.py:**

```python
@router.get("/api/orders")
async def get_orders(
    status: Optional[str] = None,
    table_code: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Список заказов с фильтрами"""
    query = db.query(Order)

    if status:
        query = query.filter(Order.status == status)
    if table_code:
        query = query.filter(Order.table_code == table_code)

    orders = query.order_by(Order.created_at.desc()).limit(limit).all()
    return orders

@router.post("/api/orders/{order_id}/print")
async def print_order(order_id: int, db: Session = Depends(get_db)):
    """Печать всего заказа"""
    service = OrderService(db)
    result = await service.print_order(order_id)
    return result

@router.post("/api/orders/{order_id}/items/{item_id}/print")
async def print_order_item(order_id: int, item_id: int, db: Session = Depends(get_db)):
    """Точечная печать блюда"""
    service = OrderService(db)
    result = await service.print_order_item(order_id, item_id)
    return result

@router.post("/api/orders/{order_id}/items/{item_id}/reprint")
async def reprint_order_item(order_id: int, item_id: int, db: Session = Depends(get_db)):
    """Переотпечатка блюда"""
    service = OrderService(db)
    result = await service.reprint_order_item(order_id, item_id)
    return result

@router.delete("/api/orders/{order_id}/print")
async def cancel_print(order_id: int, db: Session = Depends(get_db)):
    """Отмена печати заказа"""
    # Удаляем jobs в статусе QUEUED
    db.query(PrintJob).filter(
        PrintJob.order_id == order_id,
        PrintJob.status == 'QUEUED'
    ).delete()

    # Обновляем статус заказа
    order = db.query(Order).filter(Order.id == order_id).first()
    order.status = 'NOT_PRINTED'
    db.commit()

    return {"status": "ok"}
```

---

#### 2.5 WebSocket Server ⏳ (День 10)

**backend/app/api/websocket.py:**

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Клиент может отправлять ping для keep-alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

**Использование в OrderService:**
```python
from app.api.websocket import manager

# При создании заказа
await manager.broadcast({
    "type": "order_new",
    "order_id": order.id,
    "data": order.to_dict()
})

# При изменении статуса
await manager.broadcast({
    "type": "order_status",
    "order_id": order.id,
    "status": "PRINTING"
})
```

---

### Результат Недели 2

✅ **Готово:**
- RKeeper webhook handler
- XML parser
- Интеграция с dishes_with_extras.sqlite
- OrderService (создание заказов, генерация print jobs)
- Orders REST API (GET, POST print, DELETE cancel)
- WebSocket server для real-time обновлений

✅ **Можно протестировать:**
```bash
# Отправить webhook от RKeeper
curl -X POST http://localhost:8000/api/webhook/rkeeper \
  -H "Content-Type: text/xml" \
  -d '<a name="Save Order">...</a>'

# Получить список заказов
curl http://localhost:8000/api/orders

# Напечатать заказ
curl -X POST http://localhost:8000/api/orders/1/print
```

---

## 📦 Неделя 3: Frontend Orders Board

### Цель
Операторы видят доску заказов в реальном времени, могут печатать заказы.

### Задачи

#### 3.1 React Project Setup ⏳ (День 11)

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**package.json (дополнительные пакеты):**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "zustand": "^4.4.7"
  }
}
```

**Структура:**
```
frontend/src/
├── components/
│   ├── OrderBoard/
│   │   ├── OrderCard.tsx
│   │   ├── OrderFilters.tsx
│   │   └── OrderBoard.tsx
│   ├── Layout/
│   │   ├── Navbar.tsx
│   │   └── Layout.tsx
│   └── Auth/
│       └── LoginForm.tsx
├── services/
│   ├── api.ts
│   └── websocket.ts
├── hooks/
│   └── useWebSocket.ts
├── stores/
│   └── ordersStore.ts
├── types/
│   └── index.ts
├── App.tsx
└── main.tsx
```

---

#### 3.2 API Client ⏳ (День 11)

**frontend/src/services/api.ts:**

```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Order {
  id: number;
  visit_id: string;
  order_ident: string;
  table_code: string;
  order_total: number;
  status: 'NOT_PRINTED' | 'QUEUED' | 'PRINTING' | 'DONE' | 'FAILED';
  created_at: string;
  items: OrderItem[];
}

export interface OrderItem {
  id: number;
  rk_code: string;
  dish_name: string;
  quantity: number;
  weight_g: number;
  printed_count: number;
}

class ApiClient {
  async getOrders(filters?: {
    status?: string;
    table_code?: string;
  }): Promise<Order[]> {
    const params = new URLSearchParams(filters as any);
    const response = await fetch(`${API_URL}/api/orders?${params}`);
    return response.json();
  }

  async printOrder(orderId: number): Promise<void> {
    await fetch(`${API_URL}/api/orders/${orderId}/print`, {
      method: 'POST',
    });
  }

  async printOrderItem(orderId: number, itemId: number): Promise<void> {
    await fetch(`${API_URL}/api/orders/${orderId}/items/${itemId}/print`, {
      method: 'POST',
    });
  }

  async reprintOrderItem(orderId: number, itemId: number): Promise<void> {
    await fetch(`${API_URL}/api/orders/${orderId}/items/${itemId}/reprint`, {
      method: 'POST',
    });
  }

  async cancelPrint(orderId: number): Promise<void> {
    await fetch(`${API_URL}/api/orders/${orderId}/print`, {
      method: 'DELETE',
    });
  }
}

export const api = new ApiClient();
```

---

#### 3.3 WebSocket Hook ⏳ (День 12)

**frontend/src/hooks/useWebSocket.ts:**

```typescript
import { useEffect, useState } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

export function useWebSocket(onMessage: (data: any) => void) {
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      setConnected(true);
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };

    ws.onclose = () => {
      setConnected(false);
      console.log('WebSocket disconnected');
    };

    // Переподключение через 5 сек
    const interval = setInterval(() => {
      if (ws.readyState === WebSocket.CLOSED) {
        window.location.reload();
      }
    }, 5000);

    return () => {
      clearInterval(interval);
      ws.close();
    };
  }, [onMessage]);

  return { connected };
}
```

---

#### 3.4 Orders Store (Zustand) ⏳ (День 12)

**frontend/src/stores/ordersStore.ts:**

```typescript
import { create } from 'zustand';
import { Order } from '../services/api';

interface OrdersStore {
  orders: Order[];
  setOrders: (orders: Order[]) => void;
  addOrder: (order: Order) => void;
  updateOrderStatus: (orderId: number, status: string) => void;
  filters: {
    status?: string;
    table_code?: string;
    search?: string;
  };
  setFilters: (filters: any) => void;
}

export const useOrdersStore = create<OrdersStore>((set) => ({
  orders: [],
  setOrders: (orders) => set({ orders }),
  addOrder: (order) => set((state) => ({
    orders: [order, ...state.orders]
  })),
  updateOrderStatus: (orderId, status) => set((state) => ({
    orders: state.orders.map((o) =>
      o.id === orderId ? { ...o, status } : o
    )
  })),
  filters: {},
  setFilters: (filters) => set({ filters }),
}));
```

---

#### 3.5 OrderCard Component ⏳ (День 13)

**frontend/src/components/OrderBoard/OrderCard.tsx:**

```typescript
import React, { useState } from 'react';
import { Order } from '../../services/api';

interface Props {
  order: Order;
  onPrintOrder: (orderId: number) => void;
  onPrintItem: (orderId: number, itemId: number) => void;
  onReprint: (orderId: number, itemId: number) => void;
}

const STATUS_COLORS = {
  NOT_PRINTED: 'bg-yellow-100 border-yellow-400',
  QUEUED: 'bg-blue-100 border-blue-400',
  PRINTING: 'bg-purple-100 border-purple-400',
  DONE: 'bg-green-100 border-green-400',
  FAILED: 'bg-red-100 border-red-400',
};

const STATUS_LABELS = {
  NOT_PRINTED: 'Новый',
  QUEUED: 'В очереди',
  PRINTING: 'Печатается',
  DONE: 'Готово',
  FAILED: 'Ошибка',
};

export function OrderCard({ order, onPrintOrder, onPrintItem, onReprint }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`p-4 rounded-lg border-2 ${STATUS_COLORS[order.status]} cursor-pointer transition-all`}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Заголовок */}
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-bold text-lg">Заказ #{order.order_ident}</h3>
          <p className="text-sm text-gray-600">Стол {order.table_code}</p>
          <p className="text-xs text-gray-500">
            {new Date(order.created_at).toLocaleTimeString('ru-RU', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>
        <div>
          <span className="px-2 py-1 bg-white rounded text-sm font-medium">
            {STATUS_LABELS[order.status]}
          </span>
        </div>
      </div>

      {/* Сумма */}
      {order.order_total && (
        <p className="mt-2 font-bold text-lg">{order.order_total} ₽</p>
      )}

      {/* Раскрытый вид */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-gray-300" onClick={(e) => e.stopPropagation()}>
          {/* Список блюд */}
          <div className="space-y-2">
            {order.items.map((item) => (
              <div key={item.id} className="flex justify-between items-center bg-white p-2 rounded">
                <div>
                  <p className="font-medium">{item.dish_name} x{item.quantity}</p>
                  <p className="text-xs text-gray-500">{item.weight_g}г</p>
                  {item.printed_count > 0 && (
                    <p className="text-xs text-blue-600">Напечатано: {item.printed_count}</p>
                  )}
                </div>
                <div className="space-x-2">
                  <button
                    onClick={() => onPrintItem(order.id, item.id)}
                    className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                  >
                    Печать
                  </button>
                  {item.printed_count > 0 && (
                    <button
                      onClick={() => onReprint(order.id, item.id)}
                      className="px-3 py-1 bg-gray-500 text-white rounded text-sm hover:bg-gray-600"
                    >
                      Переотпечатать
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Кнопки заказа */}
          <div className="mt-4 flex space-x-2">
            <button
              onClick={() => onPrintOrder(order.id)}
              className="flex-1 px-4 py-2 bg-green-500 text-white rounded font-medium hover:bg-green-600"
            >
              Печать всего заказа
            </button>
            <button
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
            >
              История
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

---

#### 3.6 OrderBoard Component ⏳ (День 14)

**frontend/src/components/OrderBoard/OrderBoard.tsx:**

```typescript
import React, { useEffect } from 'react';
import { useOrdersStore } from '../../stores/ordersStore';
import { api } from '../../services/api';
import { useWebSocket } from '../../hooks/useWebSocket';
import { OrderCard } from './OrderCard';

export function OrderBoard() {
  const { orders, setOrders, addOrder, updateOrderStatus, filters } = useOrdersStore();

  // WebSocket
  const { connected } = useWebSocket((data) => {
    if (data.type === 'order_new') {
      addOrder(data.data);
    } else if (data.type === 'order_status') {
      updateOrderStatus(data.order_id, data.status);
    }
  });

  // Загрузка заказов
  useEffect(() => {
    api.getOrders(filters).then(setOrders);
  }, [filters]);

  // Сортировка: FAILED, NOT_PRINTED сверху, DONE снизу
  const sortedOrders = [...orders].sort((a, b) => {
    const priority = {
      FAILED: 0,
      NOT_PRINTED: 1,
      QUEUED: 2,
      PRINTING: 3,
      DONE: 4,
    };
    return priority[a.status] - priority[b.status];
  });

  // Фильтрация
  const filteredOrders = sortedOrders.filter((order) => {
    if (filters.status && order.status !== filters.status) return false;
    if (filters.table_code && order.table_code !== filters.table_code) return false;
    if (filters.search) {
      const search = filters.search.toLowerCase();
      if (!order.order_ident.toLowerCase().includes(search) &&
          !order.table_code.toLowerCase().includes(search)) {
        return false;
      }
    }
    return true;
  });

  return (
    <div className="p-6">
      {/* Заголовок */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Заказы</h1>
        <div className="flex items-center space-x-2">
          <span className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
          <span className="text-sm">{connected ? 'Онлайн' : 'Офлайн'}</span>
        </div>
      </div>

      {/* Фильтры */}
      {/* TODO: OrderFilters компонент */}

      {/* Grid карточек */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filteredOrders.map((order) => (
          <OrderCard
            key={order.id}
            order={order}
            onPrintOrder={(id) => api.printOrder(id)}
            onPrintItem={(oid, iid) => api.printOrderItem(oid, iid)}
            onReprint={(oid, iid) => api.reprintOrderItem(oid, iid)}
          />
        ))}
      </div>

      {filteredOrders.length === 0 && (
        <div className="text-center text-gray-500 mt-12">
          <p className="text-xl">Нет заказов</p>
        </div>
      )}
    </div>
  );
}
```

---

### Результат Недели 3

✅ **Готово:**
- React app (Vite + TypeScript + Tailwind)
- API client
- WebSocket hook (real-time обновления)
- OrderBoard component (grid карточек, сортировка, фильтрация)
- OrderCard component (раскрытие, печать заказа/блюда, переотпечатка)

✅ **Можно протестировать:**
- Открыть `http://localhost:5173`
- Увидеть доску заказов
- Нажать на карточку → раскрывается список блюд
- Нажать "Печать" → этикетка печатается

---

## 📦 Неделя 4: Settings + Templates + Users

### Цель
Админ может настраивать принтер, шаблоны, пользователей через UI.

### Задачи

#### 4.1 Settings UI ⏳ (День 15-16)

**frontend/src/components/Settings/Settings.tsx:**

```typescript
// Форма настроек:
// - Принтер (IP, порт, тест печати)
// - StoreHouse (URL, логин, пароль, период sync, кнопка "Синхронизировать")
// - Фильтр столов (загрузка из RKeeper, чекбоксы)
// - Архивация (удалять заказы старше N часов)
```

**Backend endpoints:**
```python
@router.get("/api/settings")
@router.put("/api/settings")
@router.post("/api/settings/printer/test")
@router.post("/api/settings/sh5/sync")
@router.get("/api/settings/tables")  # Загрузка столов из RKeeper
```

---

#### 4.2 Templates CRUD ⏳ (День 17-18)

**frontend/src/components/Templates/Templates.tsx:**

```typescript
// Список шаблонов
// Форма редактирования (упрощённая, без canvas):
// - Название
// - Размер бумаги (ширина, высота, GAP)
// - Срок годности (часы)
// - Чекбоксы элементов (логотип, название, БЖУ, состав, штрих-код)
// - Загрузка логотипа (BMP)
// - Превью (статичное изображение)
// - Кнопка "Тест печати"
```

**Backend endpoints:**
```python
@router.get("/api/templates")
@router.post("/api/templates")
@router.put("/api/templates/{id}")
@router.delete("/api/templates/{id}")
@router.post("/api/templates/{id}/test")
```

---

#### 4.3 Users Management ⏳ (День 19)

**frontend/src/components/Users/Users.tsx:**

```typescript
// Таблица пользователей (только для admin)
// Форма добавления:
// - Логин
// - Пароль
// - Роль (operator/admin)
// Кнопка удаления
```

**Backend endpoints:**
```python
@router.get("/api/users")  # Только admin
@router.post("/api/users")  # Только admin
@router.delete("/api/users/{id}")  # Только admin
@router.post("/api/users/{id}/password")  # Смена пароля
```

---

#### 4.4 Authentication ⏳ (День 20)

**backend/app/api/auth.py:**

```python
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/api/auth/login")
async def login(form: LoginForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login == form.login).first()

    if not user or not pwd_context.verify(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    # Создаём cookie-сессию
    session_id = secrets.token_hex(16)

    # Сохраняем в БД (таблица sessions)
    session = Session(
        session_id=session_id,
        user_id=user.id,
        expires_at=datetime.now() + timedelta(hours=8)
    )
    db.add(session)
    db.commit()

    response = JSONResponse({"status": "ok", "user": user.to_dict()})
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=8 * 3600
    )
    return response

@router.post("/api/auth/logout")
async def logout(response: Response, session_id: str = Cookie(None), db: Session = Depends(get_db)):
    # Удаляем сессию
    db.query(Session).filter(Session.session_id == session_id).delete()
    db.commit()

    response.delete_cookie("session_id")
    return {"status": "ok"}
```

**frontend/src/components/Auth/LoginForm.tsx:**

```typescript
// Экран логина (если не авторизован)
// Форма: логин + пароль
// После успеха → редирект на /orders
```

---

### Результат Недели 4

✅ **Готово:**
- Settings UI (принтер, StoreHouse, фильтр столов)
- Templates CRUD (создание, редактирование, тест печати)
- Users management (добавление, удаление)
- Authentication (cookie-сессии, login/logout)

---

## 📦 Неделя 5: Deployment + Testing

### Цель
Production ready сервис, готовый к установке на мини-ПК ресторана.

### Задачи

#### 5.1 systemd Service ⏳ (День 21)

**scripts/britannica-labels.service:**

```ini
[Unit]
Description=Britannica Labels Service
After=network.target

[Service]
Type=simple
User=britannica
WorkingDirectory=/opt/britannica-labels
ExecStart=/opt/britannica-labels/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Установка:**
```bash
sudo cp scripts/britannica-labels.service /etc/systemd/system/
sudo systemctl enable britannica-labels
sudo systemctl start britannica-labels
```

---

#### 5.2 nginx Reverse Proxy ⏳ (День 21)

**scripts/nginx.conf:**

```nginx
server {
    listen 80;
    server_name labels.local;

    # Frontend
    location / {
        root /opt/britannica-labels/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

---

#### 5.3 Backup Scripts ⏳ (День 22)

**scripts/backup.sh:**

```bash
#!/bin/bash
BACKUP_DIR="/opt/britannica-labels/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup SQLite
sqlite3 /opt/britannica-labels/backend/britannica.sqlite ".backup '${BACKUP_DIR}/britannica_${DATE}.sqlite'"

# Backup dishes_with_extras.sqlite
cp /opt/britannica-labels/dishes_with_extras.sqlite ${BACKUP_DIR}/dishes_${DATE}.sqlite

# Удаляем старые бекапы (> 7 дней)
find ${BACKUP_DIR} -name "*.sqlite" -mtime +7 -delete

echo "Backup completed: ${DATE}"
```

**Cron:**
```bash
0 2 * * * /opt/britannica-labels/scripts/backup.sh
```

---

#### 5.4 Testing ⏳ (День 23-24)

**backend/tests/:**
```bash
pytest backend/tests/test_tspl_renderer.py
pytest backend/tests/test_printer_client.py
pytest backend/tests/test_order_service.py
pytest backend/tests/test_api.py
```

**Тестирование на мини-ПК:**
1. Установить на мини-ПК (Ubuntu/Debian)
2. Настроить принтер (IP, тест печати)
3. Настроить RKeeper webhook
4. Отправить тестовый заказ
5. Проверить печать этикеток

---

#### 5.5 Документация ⏳ (День 25)

**docs/:**
- `API.md` — REST API endpoints
- `DATABASE.md` — схема БД
- `TSPL.md` — формат TSPL, примеры
- `DEPLOYMENT.md` — пошаговая установка

---

### Результат Недели 5

✅ **Готово:**
- systemd service (автозапуск)
- nginx reverse proxy
- Backup scripts (автоматические бекапы БД)
- Тесты (unit + integration)
- Документация
- Production-ready сервис

---

## 🎯 Критерии Готовности MVP

### Backend
- [x] SQLite база данных (7 таблиц)
- [x] ORM модели (SQLAlchemy)
- [x] TSPL renderer (с датой/сроком годности)
- [x] TCP:9100 printer client
- [x] Print queue worker (async, ретраи 3x)
- [x] RKeeper webhook handler (XML parser)
- [x] Интеграция с dishes_with_extras.sqlite
- [x] Orders API (GET, POST, DELETE)
- [x] WebSocket server (real-time)
- [x] Templates API (CRUD)
- [x] Settings API
- [x] Users API + Authentication

### Frontend
- [x] React app (TypeScript + Tailwind)
- [x] OrderBoard (grid карточек, WebSocket)
- [x] OrderCard (раскрытие, печать, переотпечатка)
- [x] Templates UI (CRUD, тест печати)
- [x] Settings UI (принтер, StoreHouse, фильтр столов)
- [x] Users UI (добавление, удаление)
- [x] LoginForm (авторизация)

### Deployment
- [x] systemd service
- [x] nginx reverse proxy
- [x] Backup scripts
- [x] Documentation

### Testing
- [x] Unit tests (backend)
- [x] Integration tests (API)
- [x] E2E tests (печать на реальном принтере)

---

## 📊 Метрики Успеха

| Метрика | Цель | Статус |
|---------|------|--------|
| Время печати 1 этикетки | < 3 сек | ⏳ |
| Время печати заказа (5 блюд) | < 15 сек | ⏳ |
| Задержка WebSocket обновления | < 500ms | ⏳ |
| Uptime сервиса | > 99% | ⏳ |
| Процент успешной печати | > 95% | ⏳ |

---

## 🔮 Roadmap v2 (после MVP)

### Фаза 2: Улучшения (6-8 недель)
- Canvas редактор шаблонов (drag & drop)
- QR-коды на этикетках (ссылка на состав, аллергены)
- Множественные принтеры (горячий цех, холодный, бар)
- Статистика (графики печати, топ блюд)
- Уведомления (Telegram бот для админов)

### Фаза 3: Масштабирование (8-10 недель)
- Multi-tenant (несколько ресторанов в одном сервисе)
- Cloud backup (S3/DigitalOcean Spaces)
- Мобильное приложение (React Native)
- Интеграция с 1С (выгрузка данных)

---

**Документ обновлён**: 19.10.2025
**Статус**: В разработке (Неделя 0)
**Следующий шаг**: Создание структуры проекта, инициализация backend/frontend
