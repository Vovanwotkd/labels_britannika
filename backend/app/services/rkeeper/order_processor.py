"""
RKeeper Order Processor
Обработка заказов от RKeeper webhook
"""

import logging
import json
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
    4. PrintJob создаются только при ручной печати (клик на заказ в UI)
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
            {
                "event_type": str,  # "New Order", "Order Changed", "Save Order", "Quit Order"
                "visit_id": str,
                "order_ident": str,
                "table_code": str,
                "order_sum": float,
                "paid": bool,
                "finished": bool,
                "total_pieces": int,
                "changes": [...]  # Изменения блюд
            }

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
            event_type = parsed_data["event_type"]
            visit_id = parsed_data["visit_id"]
            order_ident = parsed_data["order_ident"]
            table_code = parsed_data["table_code"]
            order_sum = parsed_data["order_sum"]
            paid = parsed_data["paid"]
            finished = parsed_data["finished"]
            total_pieces = parsed_data["total_pieces"]
            changes = parsed_data["changes"]

            logger.info(
                f"🔄 Processing RKeeper event: {event_type}, "
                f"visit={visit_id}, order={order_ident}, table={table_code}, "
                f"sum={order_sum:.2f}₽, paid={paid}, finished={finished}, totalPieces={total_pieces}"
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
                order_sum=order_sum,
            )

            # Сохраняем количество items ДО обработки изменений
            # (для проверки отмены заказа при удалении всех блюд)
            from app.models import OrderItem
            items_before_changes = self.db.query(OrderItem).filter(
                OrderItem.order_id == order.id
            ).count()

            # Для "Save Order" и "Quit Order" используем ПОЛНУЮ замену блюд
            # (parser возвращает полное состояние заказа из всех Session)
            # Для остальных событий - обрабатываем delta-изменения из ChangeLog
            if event_type in ['Save Order', 'Quit Order']:
                # ПОЛНАЯ ЗАМЕНА: удаляем старые блюда и создаём новые
                items_processed, jobs_created = self._replace_all_items(order, changes)
            else:
                # DELTA-ОБРАБОТКА: обрабатываем изменения из ChangeLog
                # Группируем изменения по rk_code (суммируем дубликаты с разными uni)
                grouped_changes = self._group_changes_by_rk_code(changes)

                # Обрабатываем сгруппированные изменения
                items_processed = 0
                jobs_created = 0

                for change in grouped_changes:
                    result = self._process_change(order, change)
                    items_processed += 1
                    jobs_created += result["jobs_created"]

            # Проверяем статус заказа
            # 1. Отменяем заказ если все блюда удалены (totalPieces=0) и сохранён
            #    НО только если в нём уже были блюда (не пустой новый заказ)
            if total_pieces == 0 and items_before_changes > 0:
                order.status = "CANCELLED"
                order.closed_at = datetime.now()
                logger.info(f"🚫 Order {order.id} cancelled (totalPieces=0, had {items_before_changes} items before)")

            # 2. НЕ меняем статус автоматически при оплате/закрытии заказа
            #    Статус меняется только после печати:
            #    - NOT_PRINTED → остаётся до печати
            #    - После успешной печати → DONE (в PrintQueueWorker)
            #    - После ошибки печати → FAILED (в PrintQueueWorker)
            # elif paid and finished:
            #     # Убрано - не меняем статус автоматически

            # Сохраняем всё
            self.db.commit()

            logger.info(
                f"✅ Event processed: order_id={order.id}, "
                f"changes={items_processed}, jobs={jobs_created}"
            )

            return {
                "success": True,
                "order_id": order.id,
                "message": f"{event_type} processed successfully",
                "items_processed": items_processed,
                "jobs_created": jobs_created,
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error processing event: {e}", exc_info=True)
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

    def _replace_all_items(self, order: Order, changes: list) -> tuple[int, int]:
        """
        Полная замена всех блюд в заказе

        Используется для "Save Order" и "Quit Order" когда parser
        возвращает ПОЛНОЕ состояние заказа (все Session), а не delta.

        Логика:
        1. Удаляем ВСЕ старые OrderItem
        2. Создаём новые OrderItem из changes
        3. Создаём PrintJob только для НОВЫХ порций (сравниваем с old quantities)

        Args:
            order: Order объект
            changes: Список блюд с полными quantities (из всех Session)

        Returns:
            (items_processed, jobs_created)
        """
        from app.models import OrderItem

        logger.info(f"🔄 Full replace: order_id={order.id}, new_items={len(changes)}")

        # Сохраняем старые quantities для сравнения (чтобы печатать только дельту)
        old_quantities = {}
        for old_item in order.items:
            old_quantities[old_item.rk_code] = old_item.quantity

        # Удаляем ВСЕ старые OrderItem
        for old_item in list(order.items):
            logger.debug(f"  ➖ Deleting old item: {old_item.rk_code} × {old_item.quantity}")
            self.db.delete(old_item)

        self.db.flush()

        # Создаём новые OrderItem (PrintJob создаются только при ручной печати)
        items_processed = 0

        for change in changes:
            rk_code = change["rk_code"]
            new_quantity = change["new_quantity"]

            # Получаем данные блюда из dishes_with_extras.sqlite
            dish = dishes_db.get_dish_by_rk_code(rk_code)
            if not dish:
                logger.warning(f"  ⚠️  Dish {rk_code} not found in database")
                dish = {
                    "name": change["name"],
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

            # Создаём новый OrderItem
            order_item = OrderItem(
                order_id=order.id,
                rk_code=rk_code,
                dish_name=change["name"],
                quantity=new_quantity,
                weight_g=dish["weight_g"],
            )
            self.db.add(order_item)
            self.db.flush()  # Получаем ID

            logger.info(f"  ➕ Created item: {rk_code} ({change['name']}) × {new_quantity}")

            # PrintJob НЕ создаются автоматически, только при ручной печати
            old_qty = old_quantities.get(rk_code, 0)
            delta = new_quantity - old_qty

            if delta > 0:
                logger.info(f"  📦 Added {delta} new portions (was {old_qty}, now {new_quantity}) - jobs will be created on manual print")
            elif delta < 0:
                logger.debug(f"  📉 Quantity decreased by {-delta} (was {old_qty}, now {new_quantity})")
            else:
                logger.debug(f"  ✔️  Quantity unchanged: {new_quantity}")

            items_processed += 1

        return items_processed, 0  # jobs_created = 0 (создаются только при ручной печати)

    def _group_changes_by_rk_code(self, changes: list) -> list:
        """
        Группировать изменения по rk_code и суммировать quantities

        RKeeper создаёт дубликаты с разными uni когда пользователь:
        1. Добавляет блюдо → кликает на другое → кликает на первое снова
        2. Получается два элемента с одинаковым code но разными uni

        Webhook приходит с несколькими элементами:
        - Dish code="1140" uni="4" quantity="2000"
        - Dish code="1140" uni="11" quantity="1000"

        Нужно сгруппировать их в один элемент:
        - Dish code="1140" quantity="3000" (2000 + 1000)

        Args:
            changes: Список изменений от parser

        Returns:
            Список сгруппированных изменений с суммированными quantities
        """
        from collections import defaultdict

        # Группируем по rk_code
        grouped = defaultdict(lambda: {
            "rk_code": None,
            "rk_id": None,
            "name": None,
            "uni": None,  # Берём первый uni (не важен для OrderItem)
            "old_quantity": 0,
            "new_quantity": 0,
            "delta": 0,
            "price": 0,
            "is_new": False,
            "is_deleted": False,
        })

        for change in changes:
            rk_code = change["rk_code"]
            item = grouped[rk_code]

            # Первое вхождение - заполняем базовые поля
            if item["rk_code"] is None:
                item["rk_code"] = rk_code
                item["rk_id"] = change["rk_id"]
                item["name"] = change["name"]
                item["uni"] = change["uni"]
                item["price"] = change["price"]
                item["is_new"] = change["is_new"]
                item["is_deleted"] = change["is_deleted"]

            # Суммируем quantities
            item["old_quantity"] += change["old_quantity"]
            item["new_quantity"] += change["new_quantity"]
            item["delta"] += change["delta"]

        result = list(grouped.values())

        # Логируем группировку если были дубликаты
        if len(result) < len(changes):
            logger.debug(f"  🔀 Grouped {len(changes)} changes into {len(result)} items")
            for item in result:
                if any(c["rk_code"] == item["rk_code"] for c in changes):
                    count = sum(1 for c in changes if c["rk_code"] == item["rk_code"])
                    if count > 1:
                        logger.debug(
                            f"     {item['rk_code']} ({item['name']}): "
                            f"{count} duplicates → quantity={item['new_quantity']}"
                        )

        return result

    def _get_or_create_order(
        self,
        visit_id: str,
        order_ident: str,
        table_code: str,
        order_sum: float,
    ) -> Order:
        """
        Получить существующий заказ или создать новый

        Args:
            visit_id: ID визита
            order_ident: Идентификатор заказа
            table_code: Код стола
            order_sum: Сумма заказа

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
            order.order_total = order_sum
            order.updated_at = datetime.now()

            logger.debug(f"📝 Updated existing order #{order.id}")
        else:
            # Создаём новый заказ
            order = Order(
                visit_id=visit_id,
                order_ident=order_ident,
                table_code=table_code,
                order_total=order_sum,
                status="NOT_PRINTED",  # Изначально не напечатано
            )
            self.db.add(order)
            self.db.flush()  # Получаем ID

            logger.debug(f"➕ Created new order #{order.id}")

        return order

    def _process_change(self, order: Order, change: Dict) -> Dict:
        """
        Обработать изменение блюда в заказе

        Args:
            order: Order объект
            change: Данные изменения от parser
            {
                "rk_code": str,
                "rk_id": str,
                "name": str,
                "uni": int,
                "old_quantity": int,
                "new_quantity": int,
                "delta": int,
                "price": float,
                "is_new": bool,
                "is_deleted": bool,
            }

        Returns:
            {
                "jobs_created": int
            }
        """
        rk_code = change["rk_code"]
        uni = change["uni"]
        new_quantity = change["new_quantity"]
        delta = change["delta"]
        is_new = change["is_new"]
        is_deleted = change["is_deleted"]

        logger.debug(
            f"  📦 Processing change: rk_code={rk_code}, uni={uni}, "
            f"qty: {change['old_quantity']}→{new_quantity} (Δ{delta:+d}), "
            f"new={is_new}, deleted={is_deleted}"
        )

        # Получаем данные блюда из dishes_with_extras.sqlite
        dish = dishes_db.get_dish_by_rk_code(rk_code)
        if not dish:
            logger.warning(f"  ⚠️  Dish {rk_code} not found in database")
            # Создаём dish с базовыми данными из RKeeper
            dish = {
                "name": change["name"],
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

        # Ищем существующий OrderItem с таким uni
        order_item = self.db.query(OrderItem).filter(
            OrderItem.order_id == order.id,
            OrderItem.rk_code == rk_code,
        ).first()

        jobs_created = 0

        if is_deleted or new_quantity == 0:
            # Блюдо удалено из заказа
            if order_item:
                logger.debug(f"  ➖ Deleting order_item #{order_item.id}")
                self.db.delete(order_item)
            else:
                logger.debug(f"  ⏭️  Item already deleted, skipping")
            return {"jobs_created": 0}

        if order_item:
            # Обновляем существующий OrderItem
            old_qty = order_item.quantity
            order_item.quantity = new_quantity
            order_item.dish_name = change["name"]

            logger.debug(f"  📝 Updated order_item #{order_item.id}: {old_qty}→{new_quantity}")

            # PrintJob НЕ создаются автоматически, только при ручной печати
            if delta > 0:
                logger.debug(f"  📦 Added {delta} new portions (jobs will be created on manual print)")
        else:
            # Создаём новый OrderItem
            order_item = OrderItem(
                order_id=order.id,
                rk_code=rk_code,
                dish_name=change["name"],
                quantity=new_quantity,
                weight_g=dish["weight_g"],
            )
            self.db.add(order_item)
            self.db.flush()  # Получаем ID

            logger.debug(f"  ➕ Created order_item #{order_item.id}")

            # PrintJob НЕ создаются автоматически
            logger.debug(f"  📦 Added {new_quantity} portions (jobs will be created on manual print)")

        return {"jobs_created": jobs_created}

    def _create_print_jobs(self, order_item: OrderItem, dish: Dict, quantity: int) -> int:
        """
        Создать PrintJob для order_item

        Args:
            order_item: OrderItem объект
            dish: Данные блюда из dishes_with_extras.sqlite
            quantity: Количество порций для печати

        Returns:
            Количество созданных jobs
        """
        # Получаем шаблон
        template = self._get_default_template()
        renderer = TSPLRenderer(template.config)

        jobs_created = 0

        # Создаём основные этикетки (по количеству порций)
        for i in range(quantity):
            dish_data = {
                "name": dish["name"],
                "rk_code": dish["rkeeper_code"],
                "weight_g": dish["weight_g"],
                "calories": dish["calories"],
                "protein": dish["protein"],
                "fat": dish["fat"],
                "carbs": dish["carbs"],
                "ingredients": dish["ingredients"],
                "label_type": "MAIN",
            }

            tspl = renderer.render(dish_data)

            job = PrintJob(
                order_id=order_item.order_id,
                order_item_id=order_item.id,
                label_type="MAIN",
                tspl_data=tspl,
                dish_data_json=json.dumps(dish_data, ensure_ascii=False),
                status="QUEUED",
                retry_count=0,
                max_retries=3,
            )
            self.db.add(job)
            jobs_created += 1

        # Создаём дополнительные этикетки (если есть)
        if dish.get("has_extra_labels") and dish.get("extra_labels"):
            for extra in dish["extra_labels"]:
                for i in range(quantity):
                    extra_dish_data = {
                        "name": extra["extra_dish_name"],
                        "rk_code": dish["rkeeper_code"],
                        "weight_g": extra["extra_dish_weight_g"],
                        "calories": extra["extra_dish_calories"],
                        "protein": extra.get("extra_dish_protein", 0),
                        "fat": extra.get("extra_dish_fat", 0),
                        "carbs": extra.get("extra_dish_carbs", 0),
                        "ingredients": [],
                        "label_type": "EXTRA",
                    }

                    tspl = renderer.render(extra_dish_data)

                    job = PrintJob(
                        order_id=order_item.order_id,
                        order_item_id=order_item.id,
                        label_type="EXTRA",
                        tspl_data=tspl,
                        dish_data_json=json.dumps(extra_dish_data, ensure_ascii=False),
                        status="QUEUED",
                        retry_count=0,
                        max_retries=3,
                    )
                    self.db.add(job)
                    jobs_created += 1

        logger.debug(f"    🖨️  Created {jobs_created} print jobs")

        return jobs_created

    def _create_print_jobs_for_delta(self, order_item: OrderItem, dish: Dict, delta: int) -> int:
        """
        Создать PrintJob для дельты (только новые порции)

        Args:
            order_item: OrderItem объект
            dish: Данные блюда из dishes_with_extras.sqlite
            delta: Количество НОВЫХ порций

        Returns:
            Количество созданных jobs
        """
        return self._create_print_jobs(order_item, dish, delta)

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
