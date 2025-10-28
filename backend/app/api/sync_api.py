"""
API для управления синхронизацией с StoreHouse 5
"""

import asyncio
import subprocess
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth_api import get_current_user
from app.models import Setting, User
from app.services.sync_orders import sync_orders_with_rkeeper

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/trigger")
async def trigger_sync(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Запустить синхронизацию StoreHouse 5 вручную
    """
    # Только admin может запускать синхронизацию
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Только администратор может запускать синхронизацию")

    try:
        # Обновляем время последней синхронизации
        sync_last_setting = db.query(Setting).filter(Setting.key == "sh5_sync_last").first()
        if sync_last_setting:
            sync_last_setting.value = datetime.now().isoformat()
        else:
            db.add(Setting(key="sh5_sync_last", value=datetime.now().isoformat()))

        # Очищаем предыдущие ошибки
        sync_error_setting = db.query(Setting).filter(Setting.key == "sh5_sync_error").first()
        if sync_error_setting:
            sync_error_setting.value = None

        db.commit()

        # Запускаем sync скрипт в фоне
        # Используем subprocess для запуска скрипта асинхронно
        process = subprocess.Popen(
            ["python", "/app/export_dishes_full.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        return {
            "status": "started",
            "message": "Синхронизация запущена в фоновом режиме",
            "pid": process.pid,
            "started_at": datetime.now().isoformat()
        }

    except Exception as e:
        # Сохраняем ошибку в БД
        sync_error_setting = db.query(Setting).filter(Setting.key == "sh5_sync_error").first()
        if sync_error_setting:
            sync_error_setting.value = str(e)
        else:
            db.add(Setting(key="sh5_sync_error", value=str(e)))
        db.commit()

        raise HTTPException(status_code=500, detail=f"Ошибка запуска синхронизации: {str(e)}")


@router.get("/status")
async def get_sync_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Получить статус синхронизации
    """
    # Читаем настройки из БД
    sync_last = db.query(Setting).filter(Setting.key == "sh5_sync_last").first()
    sync_error = db.query(Setting).filter(Setting.key == "sh5_sync_error").first()
    sync_interval = db.query(Setting).filter(Setting.key == "sync_interval_hours").first()

    return {
        "last_sync": sync_last.value if sync_last else None,
        "last_error": sync_error.value if sync_error else None,
        "interval_hours": int(sync_interval.value) if sync_interval and sync_interval.value else 24
    }


@router.post("/orders")
async def sync_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Синхронизировать заказы с RKeeper вручную

    Запускает синхронизацию заказов из RKeeper.
    Обновляет статусы существующих заказов и создаёт пропущенные.
    """
    try:
        result = await sync_orders_with_rkeeper(db)

        return {
            "status": "success" if result["success"] else "error",
            "fetched_from_rkeeper": result["fetched_from_rkeeper"],
            "orders_created": result["orders_created"],
            "orders_updated": result["orders_updated"],
            "orders_marked_done": result["orders_marked_done"],
            "orders_marked_cancelled": result["orders_marked_cancelled"],
            "message": result["message"],
            "synced_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка синхронизации заказов с RKeeper: {str(e)}"
        )
