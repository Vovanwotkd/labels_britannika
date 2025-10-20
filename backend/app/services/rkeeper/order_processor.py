"""
RKeeper Order Processor
Обработка заказов от RKeeper webhook
"""

import logging
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import dishes_db
from app.models import Order, OrderItem, PrintJob, Template
from app.services.printer.tspl_renderer import TSPLRenderer

logger = logging.getLogger(__name__)


class OrderProcessor:
    """
    Обработчик заказов от RKeeper

    Логика:
    1. Получаем parsed данные от XML parser
    2. Создаём/обновляем Order в БД
    3. Создаём OrderItem для каждого блюда
    4. Автоматически создаём PrintJob (статус QUEUED)
    5. PrintQueueWorker подхватит задания и напечатает
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Database session
        """
        self.db = db

    def process(self, parsed_data: Dict) -> Dict:
        """
        Обработать заказ от RKeeper

        Args:
            parsed_data: Parsed данные от RKeeperXMLParser

        Returns:
            {
                "success": bool,
                "order_id": Optional[int],
                "message": str,
                "items_processed": int,
                "jobs_created": int,
            }
        """
        try:
            action = parsed_data["action"]
            visit_id = parsed_data["visit_id"]
            order_ident = parsed_data["order_ident"]
            table_code = parsed_data["table_code"]
            items_data = parsed_data["items"]

            logger.info(
                f"🔄 Processing RKeeper order: action={action}, "
                f"visit={visit_id}, order={order_ident}, table={table_code}"
            )

            # Проверяем фильтр столов (если настроен)
            if not self._check_table_filter(table_code):
                logger.info(f"⏭️  Table {table_code} excluded by filter, skipping")
                return {
                    "success": True,
                    "order_id": None,
                    "message": f"Table {table_code} excluded by filter",
                    "items_processed": 0,
                    "jobs_created": 0,
                }

            # Ищем существующий заказ или создаём новый
            order = self._get_or_create_order(
                visit_id=visit_id,
                order_ident=order_ident,
                table_code=table_code,
                table_name=parsed_data.get("table_name", ""),
                waiter_code=parsed_data.get("waiter_code"),
                waiter_name=parsed_data.get("waiter_name"),
            )

            # Обрабатываем items
            items_processed = 0
            jobs_created = 0

            for item_data in items_data:
                result = self._process_item(order, item_data)
                items_processed += 1
                jobs_created += result["jobs_created"]

            # Сохраняем всё
            self.db.commit()

            logger.info(
                f"✅ Order processed: order_id={order.id}, "
                f"items={items_processed}, jobs={jobs_created}"
            )

            return {
                "success": True,
                "order_id": order.id,
                "message": "Order processed successfully",
                "items_processed": items_processed,
                "jobs_created": jobs_created,
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error processing order: {e}", exc_info=True)
            return {
                "success": False,
                "order_id": None,
                "message": str(e),
                "items_processed": 0,
                "jobs_created": 0,
            }

    def _check_table_filter(self, table_code: str) -> bool:
        """
        Проверить попадает ли стол в фильтр

        Args:
            table_code: Код стола

        Returns:
            True если нужно обрабатывать, False если пропустить
        """
        from app.models import TableFilter

        # Получаем активные фильтры для данного стола
        filter_entry = self.db.query(TableFilter).filter(
            TableFilter.table_code == table_code,
            TableFilter.enabled == True
        ).first()

        if filter_entry:
            # Стол найден в фильтре и активен - обрабатываем
            return True

        # Проверяем, есть ли вообще какие-то фильтры в базе
        any_filters = self.db.query(TableFilter).filter(
            TableFilter.enabled == True
        ).count()

        if any_filters > 0:
            # Фильтры есть, но данного стола в них нет - пропускаем
            logger.info(f"⏭️  Table {table_code} not in selected tables, skipping")
            return False

        # Фильтров нет вообще - обрабатываем все столы
        return True

    def _get_or_create_order(
        self,
        visit_id: str,
        order_ident: str,
        table_code: str,
        table_name: str,
        waiter_code: Optional[str],
        waiter_name: Optional[str],
    ) -> Order:
        """
        Получить существующий заказ или создать новый

        Args:
            visit_id: ID визита
            order_ident: Идентификатор заказа
            table_code: Код стола
            table_name: Название стола
            waiter_code: Код официанта
            waiter_name: Имя официанта

        Returns:
            Order объект
        """
        # Ищем существующий заказ
        order = self.db.query(Order).filter(
            Order.visit_id == visit_id,
            Order.order_ident == order_ident,
        ).first()

        if order:
            # Обновляем данные заказа (на случай изменений)
            order.table_code = table_code
            order.table_name = table_name
            order.waiter_code = waiter_code
            order.waiter_name = waiter_name
            order.updated_at = datetime.now()

            logger.debug(f"📝 Updated existing order #{order.id}")
        else:
            # Создаём новый заказ
            order = Order(
                visit_id=visit_id,
                order_ident=order_ident,
                table_code=table_code,
                table_name=table_name,
                waiter_code=waiter_code,
                waiter_name=waiter_name,
                status="NOT_PRINTED",  # Изначально не напечатано
            )
            self.db.add(order)
            self.db.flush()  # Получаем ID

            logger.debug(f"➕ Created new order #{order.id}")

        return order

    def _process_item(self, order: Order, item_data: Dict) -> Dict:
        """
        Обработать item (блюдо) заказа

        Args:
            order: Order объект
            item_data: Данные item от parser

        Returns:
            {
                "jobs_created": int
            }
        """
        rk_code = item_data["rk_code"]
        uni = item_data["uni"]
        quantity = item_data["quantity"]

        logger.debug(f"  📦 Processing item: rk_code={rk_code}, uni={uni}, qty={quantity}")

        # Пропускаем если quantity = 0 (удалено из заказа)
        if quantity <= 0:
            logger.debug(f"  ⏭️  Item {rk_code} has quantity=0, skipping")
            return {"jobs_created": 0}

        # Получаем данные блюда из dishes_with_extras.sqlite
        dish = dishes_db.get_dish_by_rk_code(rk_code)
        if not dish:
            logger.warning(f"  ⚠️  Dish {rk_code} not found in database")
            # Создаём item с базовыми данными из RKeeper
            dish = {
                "name": item_data["name"],
                "rkeeper_code": rk_code,
                "weight_g": 0,
                "calories": 0,
                "protein": 0,
                "fat": 0,
                "carbs": 0,
                "ingredients": [],
                "has_extra_labels": False,
                "extra_labels": [],
            }

        # Ищем существующий OrderItem или создаём новый
        order_item = self.db.query(OrderItem).filter(
            OrderItem.order_id == order.id,
            OrderItem.uni == uni,
        ).first()

        if order_item:
            # Обновляем существующий
            order_item.quantity = quantity
            order_item.updated_at = datetime.now()

            logger.debug(f"  📝 Updated order_item #{order_item.id}")
        else:
            # Создаём новый
            order_item = OrderItem(
                order_id=order.id,
                rk_code=rk_code,
                name=item_data["name"],
                uni=uni,
                quantity=quantity,
                price=item_data["price"],
                modifier_id=item_data.get("modifier_id"),
                modifier_name=item_data.get("modifier_name"),
            )
            self.db.add(order_item)
            self.db.flush()  # Получаем ID

            logger.debug(f"  ➕ Created order_item #{order_item.id}")

        # Создаём PrintJob для этого item
        jobs_created = self._create_print_jobs(order_item, dish)

        return {"jobs_created": jobs_created}

    def _create_print_jobs(self, order_item: OrderItem, dish: Dict) -> int:
        """
        Создать PrintJob для order_item

        Args:
            order_item: OrderItem объект
            dish: Данные блюда из dishes_with_extras.sqlite

        Returns:
            Количество созданных jobs
        """
        # Получаем шаблон
        template = self._get_default_template()
        renderer = TSPLRenderer(template.config)

        jobs_created = 0

        # Создаём основные этикетки (по количеству порций)
        for i in range(order_item.quantity):
            tspl = renderer.render({
                "name": dish["name"],
                "rk_code": dish["rkeeper_code"],
                "weight_g": dish["weight_g"],
                "calories": dish["calories"],
                "protein": dish["protein"],
                "fat": dish["fat"],
                "carbs": dish["carbs"],
                "ingredients": dish["ingredients"],
                "label_type": "MAIN",
            })

            job = PrintJob(
                order_item_id=order_item.id,
                tspl_data=tspl,
                status="QUEUED",
                retry_count=0,
                max_retries=3,
            )
            self.db.add(job)
            jobs_created += 1

        # Создаём дополнительные этикетки (если есть)
        if dish.get("has_extra_labels") and dish.get("extra_labels"):
            for extra in dish["extra_labels"]:
                for i in range(order_item.quantity):
                    tspl = renderer.render({
                        "name": extra["extra_dish_name"],
                        "rk_code": dish["rkeeper_code"],
                        "weight_g": extra["extra_dish_weight_g"],
                        "calories": extra["extra_dish_calories"],
                        "protein": extra.get("extra_dish_protein", 0),
                        "fat": extra.get("extra_dish_fat", 0),
                        "carbs": extra.get("extra_dish_carbs", 0),
                        "ingredients": [],
                        "label_type": "EXTRA",
                    })

                    job = PrintJob(
                        order_item_id=order_item.id,
                        tspl_data=tspl,
                        status="QUEUED",
                        retry_count=0,
                        max_retries=3,
                    )
                    self.db.add(job)
                    jobs_created += 1

        logger.debug(f"    🖨️  Created {jobs_created} print jobs")

        return jobs_created

    def _get_default_template(self) -> Template:
        """
        Получить шаблон по умолчанию

        Returns:
            Template объект
        """
        template = self.db.query(Template).filter(
            Template.is_default == True
        ).first()

        if not template:
            raise ValueError("Default template not found")

        return template
