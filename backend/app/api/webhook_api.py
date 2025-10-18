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
        logger.debug(f"XML data:\n{xml_data}")

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
