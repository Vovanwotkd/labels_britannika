"""
Order Synchronization Service
Синхронизация заказов с RKeeper (автоматическая и ручная)
"""

import logging
from typing import Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import Order
from app.services.rkeeper_client import get_rkeeper_client
from app.services.websocket.manager import broadcast_order_update

logger = logging.getLogger(__name__)


class OrderSyncService:
    """
    Сервис синхронизации заказов с RKeeper

    Синхронизирует:
    - Все активные заказы (onlyOpened=True)
    - Обновляет статусы существующих заказов
    - Создает недостающие заказы (защита от пропущенных webhooks)
    - Предотвращает дубликаты
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Database session
        """
        self.db = db
        self.rkeeper_client = get_rkeeper_client()

    async def sync_orders(self) -> Dict:
        """
        Синхронизировать заказы с RKeeper

        Returns:
            {
                "success": bool,
                "fetched_from_rkeeper": int,
                "orders_created": int,
                "orders_updated": int,
                "orders_marked_done": int,
                "orders_marked_cancelled": int,
                "message": str,
            }
        """
        try:
            logger.info("🔄 Starting order synchronization with RKeeper...")

            # Получаем список заказов из RKeeper (только активные)
            rkeeper_orders = await self.rkeeper_client.get_order_list(only_opened=True)

            logger.info(f"📥 Fetched {len(rkeeper_orders)} orders from RKeeper")

            orders_created = 0
            orders_updated = 0
            orders_marked_done = 0
            orders_marked_cancelled = 0

            for rk_order in rkeeper_orders:
                visit_id = str(rk_order["visit_id"])
                order_ident = str(rk_order["order_ident"])
                table_code = str(rk_order["table_code"])
                order_sum = rk_order["order_sum"]
                total_pieces = rk_order["total_pieces"]
                paid = rk_order["paid"]
                finished = rk_order["finished"]

                # Проверяем, существует ли заказ в нашей БД
                existing_order = self.db.query(Order).filter(
                    Order.visit_id == visit_id,
                    Order.order_ident == order_ident,
                ).first()

                if existing_order:
                    # Заказ уже существует - обновляем его статус
                    updated = self._update_order_status(
                        existing_order,
                        total_pieces,
                        paid,
                        finished,
                        order_sum
                    )

                    if updated:
                        orders_updated += 1

                        # Проверяем что изменилось
                        if existing_order.status == "DONE":
                            orders_marked_done += 1
                        elif existing_order.status == "CANCELLED":
                            orders_marked_cancelled += 1

                        # Отправляем WebSocket уведомление об обновлении
                        await self._send_order_update(existing_order)

                else:
                    # Заказ не найден - запрашиваем детали и создаём
                    logger.warning(
                        f"⚠️  Order {visit_id}/{order_ident} not found in DB - fetching details from RKeeper"
                    )

                    try:
                        # Получаем полную информацию о заказе включая блюда
                        order_details = await self.rkeeper_client.get_order(visit_id, order_ident)

                        # Создаём заказ с блюдами
                        new_order = await self._create_order_from_rkeeper(order_details)

                        if new_order:
                            orders_created += 1

                            # Проверяем начальный статус
                            if new_order.status == "DONE":
                                orders_marked_done += 1
                            elif new_order.status == "CANCELLED":
                                orders_marked_cancelled += 1

                            # Отправляем WebSocket уведомление о новом заказе
                            await self._send_order_update(new_order)

                    except Exception as e:
                        logger.error(f"❌ Failed to create order from RKeeper: {e}")

            # Сохраняем изменения
            self.db.commit()

            logger.info(
                f"✅ Sync completed: fetched={len(rkeeper_orders)}, "
                f"created={orders_created}, updated={orders_updated}, "
                f"done={orders_marked_done}, cancelled={orders_marked_cancelled}"
            )

            return {
                "success": True,
                "fetched_from_rkeeper": len(rkeeper_orders),
                "orders_created": orders_created,
                "orders_updated": orders_updated,
                "orders_marked_done": orders_marked_done,
                "orders_marked_cancelled": orders_marked_cancelled,
                "message": f"Synchronized {len(rkeeper_orders)} orders from RKeeper",
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error synchronizing orders: {e}", exc_info=True)
            return {
                "success": False,
                "fetched_from_rkeeper": 0,
                "orders_created": 0,
                "orders_updated": 0,
                "orders_marked_done": 0,
                "orders_marked_cancelled": 0,
                "message": f"Sync failed: {str(e)}",
            }

    def _update_order_status(
        self,
        order: Order,
        total_pieces: int,
        paid: bool,
        finished: bool,
        order_sum: float,
    ) -> bool:
        """
        Обновить статус существующего заказа

        Args:
            order: Order объект
            total_pieces: Количество порций из RKeeper
            paid: Оплачен ли заказ
            finished: Завершен ли заказ
            order_sum: Сумма заказа

        Returns:
            True если статус был обновлен, False если нет изменений
        """
        old_status = order.status
        updated = False

        # Обновляем сумму заказа
        if order.order_total != order_sum:
            order.order_total = order_sum
            updated = True

        # Проверяем отмену заказа (все блюда удалены)
        if total_pieces == 0 and order.status not in ["CANCELLED", "DONE"]:
            order.status = "CANCELLED"
            order.closed_at = datetime.now()
            logger.info(f"🚫 Order {order.id} marked as CANCELLED (totalPieces=0)")
            updated = True

        # Проверяем завершение заказа (оплачен и закрыт)
        elif paid and finished and order.status not in ["DONE", "CANCELLED"]:
            order.status = "DONE"
            order.closed_at = datetime.now()
            logger.info(f"✅ Order {order.id} marked as DONE (paid and finished)")
            updated = True

        if updated:
            order.updated_at = datetime.now()
            logger.debug(
                f"📝 Order {order.id} updated: {old_status} → {order.status}, "
                f"sum={order_sum:.2f}₽, totalPieces={total_pieces}"
            )

        return updated

    async def _create_order_from_rkeeper(self, order_details: Dict) -> Order:
        """
        Создать заказ с блюдами из данных RKeeper

        Args:
            order_details: Dict с информацией о заказе (из get_order())

        Returns:
            Order объект
        """
        from app.models import OrderItem, PrintJob
        from app.services.printer.image_label_renderer import ImageLabelRenderer

        visit_id = order_details["visit_id"]
        order_ident = order_details["order_ident"]
        table_code = order_details["table_code"]
        order_sum = order_details["order_sum"]
        total_pieces = order_details["total_pieces"]
        paid = order_details["paid"]
        finished = order_details["finished"]
        dishes = order_details["dishes"]

        # Определяем начальный статус
        if total_pieces == 0:
            status = "CANCELLED"
            closed_at = datetime.now()
        elif paid and finished:
            status = "DONE"
            closed_at = datetime.now()
        else:
            status = "NOT_PRINTED"
            closed_at = None

        # Создаём Order
        order = Order(
            visit_id=visit_id,
            order_ident=order_ident,
            table_code=table_code,
            order_total=order_sum,
            status=status,
            closed_at=closed_at,
        )

        self.db.add(order)
        self.db.flush()  # Получаем ID

        logger.info(
            f"➕ Created order #{order.id} from RKeeper: "
            f"visit={visit_id}, order={order_ident}, table={table_code}, "
            f"status={status}, sum={order_sum:.2f}₽, dishes={len(dishes)}"
        )

        # Создаём OrderItem для каждого блюда
        for dish in dishes:
            logger.info(
                f"  📦 Creating OrderItem: name='{dish['dish_name']}', "
                f"quantity={dish['quantity']}, quantity_g={dish.get('quantity_g', 'N/A')}"
            )

            order_item = OrderItem(
                order_id=order.id,
                rk_code=dish["dish_code"],
                dish_name=dish["dish_name"],
                quantity=dish["quantity"],  # Уже в порциях (конвертировано в get_order)
            )
            self.db.add(order_item)
            self.db.flush()

            logger.info(f"  ✅ OrderItem created: id={order_item.id}, quantity={order_item.quantity}")

            # ПРИМЕЧАНИЕ: PrintJob создаются в OrderProcessor через webhook,
            # а не здесь. Этот блок устарел и не используется в текущей системе.
            # Оставлен для обратной совместимости, но может быть удалён.

            # # Создаём PrintJob для каждого блюда
            # try:
            #     # TODO: Этот код устарел, нужно использовать OrderProcessor
            #     pass
            # except Exception as e:
            #     logger.error(f"  ❌ Failed to create print job for {dish['dish_name']}: {e}")

        return order

    async def _send_order_update(self, order: Order) -> None:
        """
        Отправить WebSocket уведомление об изменении заказа

        Args:
            order: Order объект
        """
        try:
            # Формируем данные заказа для фронта
            order_dict = {
                "id": order.id,
                "visit_id": order.visit_id,
                "order_ident": order.order_ident,
                "table_code": order.table_code,
                "order_total": float(order.order_total) if order.order_total else 0.0,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                "closed_at": order.closed_at.isoformat() if order.closed_at else None,
            }

            # Отправляем через WebSocket правильной функцией
            # Используем event_type, чтобы фронт перезагрузил список заказов
            await broadcast_order_update(
                order_id=order.id,
                event_type="order_updated",  # Фронт проверяет message.event
                data=order_dict
            )

            logger.debug(f"📡 WebSocket notification sent for order #{order.id}")

        except Exception as e:
            logger.error(f"❌ Failed to send WebSocket notification for order #{order.id}: {e}")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def sync_orders_with_rkeeper(db: Session) -> Dict:
    """
    Удобная функция для синхронизации заказов

    Args:
        db: Database session

    Returns:
        Результат синхронизации
    """
    service = OrderSyncService(db)
    return await service.sync_orders()


def sync_single_order(db: Session, order_id: int) -> None:
    """
    Синхронизировать один заказ через GetOrder API

    Используется после webhook для корректировки quantities
    (когда RKeeper создаёт дубликаты в разных Session)

    Args:
        db: Database session
        order_id: ID заказа в нашей БД
    """
    from app.models import Order, OrderItem
    from app.services.rkeeper_client import RKeeperClient

    # Получаем заказ
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return

    # Запрашиваем актуальные данные из RKeeper
    client = RKeeperClient()
    order_data = client.get_order(order.visit_id, order.order_ident)

    if not order_data or not order_data.get('dishes'):
        return

    # Обновляем quantities из GetOrder (суммирует все Session)
    for dish_data in order_data['dishes']:
        # Ищем OrderItem по rk_code
        order_item = db.query(OrderItem).filter(
            OrderItem.order_id == order.id,
            OrderItem.rk_code == dish_data['rk_code']
        ).first()

        if order_item and order_item.quantity != dish_data['quantity']:
            logger.debug(
                f"  🔄 Synced quantity for {dish_data['rk_code']}: "
                f"{order_item.quantity}→{dish_data['quantity']}"
            )
            order_item.quantity = dish_data['quantity']

    db.commit()
