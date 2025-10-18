"""
API endpoints для печати
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.services.printer.print_service import PrintService

router = APIRouter(prefix="/api/print", tags=["print"])


# ============================================================================
# SCHEMAS (Pydantic models для валидации)
# ============================================================================

class PrintByCodeRequest(BaseModel):
    """Запрос на печать по RK коду"""
    rk_code: str
    quantity: int = 1


class PrintResponse(BaseModel):
    """Ответ на запрос печати"""
    success: bool
    message: str
    queued: int = 0  # Количество заданий добавлено в очередь


class PrinterStatusResponse(BaseModel):
    """Статус принтера"""
    online: bool
    host: str
    port: int
    error: str | None = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/test", response_model=PrintResponse)
async def test_print(db: Session = Depends(get_db)):
    """
    Тестовая печать (проверка принтера)

    Печатает тестовую этикетку с надписью "ТЕСТОВАЯ ЭТИКЕТКА"

    ПРИМЕЧАНИЕ: test_print() печатает напрямую, не через очередь
    """
    service = PrintService(db)
    result = service.test_print()

    return PrintResponse(
        success=result["success"],
        message=result["message"],
        queued=0  # Тестовая печать не использует очередь
    )


@router.post("/dish", response_model=PrintResponse)
async def print_dish(
    request: PrintByCodeRequest,
    db: Session = Depends(get_db)
):
    """
    Печать этикеток по RKeeper коду

    Args:
        rk_code: RKeeper код блюда (например, "2538")
        quantity: Количество порций (по умолчанию 1)

    Создаёт задания печати в БД:
    - Основные этикетки (по количеству порций)
    - Дополнительные этикетки (если есть в AddListSauce)

    PrintQueueWorker обработает их асинхронно
    """
    service = PrintService(db)
    result = service.print_by_rk_code(request.rk_code, request.quantity)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return PrintResponse(
        success=result["success"],
        message=result["message"],
        queued=result["queued"]
    )


@router.get("/status", response_model=PrinterStatusResponse)
async def printer_status(db: Session = Depends(get_db)):
    """
    Получить статус принтера

    Проверяет доступность принтера по TCP:9100
    """
    service = PrintService(db)
    status = service.get_printer_status()

    return PrinterStatusResponse(**status)
