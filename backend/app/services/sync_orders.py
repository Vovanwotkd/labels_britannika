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

                else:
                    # Заказ не найден - создаём новый (пропущенный webhook?)
                    logger.warning(
                        f"⚠️  Order {visit_id}/{order_ident} not found in DB - creating from RKeeper data"
                    )

                    new_order = self._create_order_from_rkeeper(
                        visit_id,
                        order_ident,
                        table_code,
                        order_sum,
                        total_pieces,
                        paid,
                        finished,
                    )

                    if new_order:
                        orders_created += 1

                        # Проверяем начальный статус
                        if new_order.status == "DONE":
                            orders_marked_done += 1
                        elif new_order.status == "CANCELLED":
                            orders_marked_cancelled += 1

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

    def _create_order_from_rkeeper(
        self,
        visit_id: str,
        order_ident: str,
        table_code: str,
        order_sum: float,
        total_pieces: int,
        paid: bool,
        finished: bool,
    ) -> Order:
        """
        Создать заказ из данных RKeeper (для пропущенных webhooks)

        Args:
            visit_id: ID визита
            order_ident: Идентификатор заказа
            table_code: Код стола
            order_sum: Сумма заказа
            total_pieces: Количество порций
            paid: Оплачен ли заказ
            finished: Завершен ли заказ

        Returns:
            Order объект
        """
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
            f"status={status}, sum={order_sum:.2f}₽"
        )

        return order


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
