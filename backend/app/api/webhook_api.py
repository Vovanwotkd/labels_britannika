"""
Webhook API - RKeeper Integration
Endpoint для приёма webhook от RKeeper
"""

import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.rkeeper.xml_parser import parse_rkeeper_xml
from app.services.rkeeper.order_processor import OrderProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/rkeeper")
async def rkeeper_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    RKeeper webhook endpoint

    Принимает XML от RKeeper при создании/изменении заказа

    Формат запроса:
    - Content-Type: text/xml
    - Body: XML с заказом

    Логика:
    1. Парсим XML
    2. Проверяем фильтр столов
    3. Создаём/обновляем Order
    4. Создаём OrderItem
    5. Автоматически создаём PrintJob (QUEUED)
    6. PrintQueueWorker подхватит и напечатает

    Возвращает:
    - HTTP 200 OK (всегда, даже при ошибках внутри)
    - RKeeper не должен получать ошибки, чтобы не ретраить
    """
    try:
        # Читаем body как text
        body = await request.body()
        xml_data = body.decode('utf-8')

        logger.info(f"📨 Received RKeeper webhook ({len(xml_data)} bytes)")

        # Проверяем настройку логирования
        from app.models.setting import Setting
        logging_setting = db.query(Setting).filter(Setting.key == "rkeeper_logging").first()
        rkeeper_logging_enabled = (
            logging_setting and
            logging_setting.value and
            logging_setting.value.lower() in ("true", "1", "yes", "y")
        )

        # Дополнительно логируем в файл если включено
        if rkeeper_logging_enabled:
            import os
            from datetime import datetime
            log_dir = "/app/data/rkeeper_logs"
            os.makedirs(log_dir, exist_ok=True)
            log_file = f"{log_dir}/webhook_{datetime.now().strftime('%Y%m%d')}.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] RKeeper Webhook\n")
                f.write(f"{'='*80}\n")
                f.write(xml_data)
                f.write(f"\n{'='*80}\n\n")
            logger.info(f"📄 Logged to {log_file}")
        else:
            logger.debug(f"📄 Raw XML:\n{xml_data}")

        # Парсим XML
        parsed_data = parse_rkeeper_xml(xml_data)

        if not parsed_data:
            logger.error("❌ Failed to parse RKeeper XML")
            # Всё равно возвращаем 200, чтобы RKeeper не ретраил
            return {"status": "error", "message": "Failed to parse XML"}

        # Обрабатываем заказ
        processor = OrderProcessor(db)
        result = processor.process(parsed_data)

        if result["success"]:
            logger.info(
                f"✅ Webhook processed: order_id={result['order_id']}, "
                f"items={result['items_processed']}, jobs={result['jobs_created']}"
            )

            # Синхронизируем правильные количества через GetOrder API
            # ТОЛЬКО если обнаружены дубликаты блюд (одинаковые rk_code в разных Session)
            # Это минимизирует нагрузку на RKeeper сервер
            if result.get('has_duplicates', False):
                logger.info("🔄 Detected duplicates, syncing quantities from GetOrder API...")
                try:
                    from app.services.rkeeper_client import RKeeperClient
                    from app.models import Order

                    order = db.query(Order).filter(Order.id == result['order_id']).first()
                    if order:
                        client = RKeeperClient()
                        order_data = client.get_order(order.visit_id, order.order_ident)

                        if order_data and order_data.get('dishes'):
                            # Обновляем количества из GetOrder (суммирует все Session)
                            from app.models import OrderItem

                            for dish_data in order_data['dishes']:
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
                            logger.info("✅ Synced quantities from GetOrder API")
                except Exception as sync_err:
                    logger.warning(f"⚠️  Failed to sync quantities from GetOrder: {sync_err}")
                    # Не падаем, продолжаем обработку

            # Отправляем WebSocket уведомление
            from app.services.websocket.manager import broadcast_order_update

            # Маппинг RKeeper событий в frontend события
            rkeeper_event = parsed_data.get('event_type', 'Order Changed')
            event_mapping = {
                'New Order': 'new_order',
                'Order Changed': 'order_updated',
                'Save Order': 'order_updated',
                'Quit Order': 'order_updated',
                'Open Order': 'order_updated',
            }
            frontend_event = event_mapping.get(rkeeper_event, 'order_updated')

            try:
                await broadcast_order_update(
                    order_id=result['order_id'],
                    event_type=frontend_event,
                    data={
                        "items_count": result.get('items_processed', 0),
                        "jobs_count": result.get('jobs_created', 0),
                    }
                )
                logger.debug(f"📢 Sent WebSocket notification for order {result['order_id']} (event={frontend_event})")
            except Exception as ws_err:
                logger.error(f"❌ Failed to send WebSocket notification: {ws_err}")
                # Не падаем, продолжаем обработку

        else:
            logger.error(f"❌ Webhook processing failed: {result['message']}")

        # Всегда возвращаем 200 OK
        return {
            "status": "ok" if result["success"] else "error",
            "message": result["message"],
            "order_id": result.get("order_id"),
            "items_processed": result.get("items_processed", 0),
            "jobs_created": result.get("jobs_created", 0),
        }

    except Exception as e:
        logger.error(f"❌ Unexpected error in webhook: {e}", exc_info=True)

        # Всё равно возвращаем 200, чтобы RKeeper не ретраил
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/test")
async def test_webhook(db: Session = Depends(get_db)):
    """
    Тестовый webhook endpoint

    Отправляет тестовый XML для проверки парсинга и обработки
    """
    # Тестовый XML
    test_xml = """<?xml version="1.0" encoding="UTF-8"?>
<RK7Query>
    <a name="Save Order">
        <Order visit="123456" orderIdent="7890">
            <Table code="101" name="Стол 1"/>
            <Waiter code="5" name="Иван Иванов"/>
            <Session>
                <Dish id="2538" code="2538" name="Борщ украинский" uni="1" quantity="1000" price="45000"/>
                <Dish id="2539" code="2539" name="Котлета по-киевски" uni="2" quantity="2000" price="35000">
                    <Modi id="123" name="С картофельным пюре"/>
                </Dish>
            </Session>
            <ChangeLog>
                <Dish id="2538" uni="1" oldvalue="0" newvalue="1000" price="45000"/>
                <Dish id="2539" uni="2" oldvalue="0" newvalue="2000" price="35000"/>
                <Modi id="123"/>
            </ChangeLog>
        </Order>
    </a>
</RK7Query>"""

    logger.info("🧪 Processing test webhook")

    # Парсим
    parsed_data = parse_rkeeper_xml(test_xml)

    if not parsed_data:
        raise HTTPException(status_code=400, detail="Failed to parse test XML")

    # Обрабатываем
    processor = OrderProcessor(db)
    result = processor.process(parsed_data)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return {
        "status": "ok",
        "message": "Test webhook processed successfully",
        "parsed_data": parsed_data,
        "result": result,
    }
