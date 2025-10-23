"""
Printers API - управление принтерами
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth_api import require_auth
from app.models import User
from app.services.printer.cups_client import CUPSPrinterClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/printers", tags=["printers"])


# ============================================================================
# SCHEMAS
# ============================================================================

class PrinterInfo(BaseModel):
    """Информация о принтере"""
    name: str
    online: bool
    status: str


class PrintersListResponse(BaseModel):
    """Список принтеров"""
    printers: List[str]
    count: int


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/list", response_model=PrintersListResponse)
async def get_cups_printers(
    current_user: User = Depends(require_auth)
):
    """
    Получить список доступных CUPS принтеров

    Требует аутентификации
    """
    try:
        # Получаем список принтеров из CUPS
        # host.docker.internal для доступа к хосту из контейнера
        printers = CUPSPrinterClient.list_printers(cups_server="host.docker.internal")

        logger.info(f"📋 Получен список CUPS принтеров: {printers}")

        return PrintersListResponse(
            printers=printers,
            count=len(printers)
        )

    except Exception as e:
        logger.error(f"❌ Ошибка получения списка принтеров: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения списка принтеров: {str(e)}")


@router.get("/{printer_name}/status", response_model=PrinterInfo)
async def get_printer_status(
    printer_name: str,
    current_user: User = Depends(require_auth)
):
    """
    Получить статус конкретного принтера

    Требует аутентификации
    """
    try:
        client = CUPSPrinterClient(
            printer_name=printer_name,
            cups_server="host.docker.internal"
        )

        status = client.get_printer_status()

        return PrinterInfo(
            name=status["printer_name"],
            online=status["online"],
            status=status["status"]
        )

    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса принтера {printer_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статуса: {str(e)}")
