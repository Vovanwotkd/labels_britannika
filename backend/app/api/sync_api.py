"""
API для управления синхронизацией с StoreHouse 5
"""

import asyncio
import subprocess
import re
from datetime import datetime
from typing import Dict, Optional

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


@router.get("/progress")
async def get_sync_progress(
    current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Получить прогресс текущей синхронизации StoreHouse

    Парсит логи sync контейнера и возвращает:
    - is_running: идёт ли синхронизация
    - progress: процент выполнения (0-100)
    - current: текущее количество обработанных товаров
    - total: общее количество товаров
    - speed: скорость обработки (items/sec)
    - eta: осталось времени
    - errors: количество ошибок
    - extra_labels: найдено дополнительных этикеток
    """
    try:
        # Читаем последние 50 строк логов sync контейнера
        result = subprocess.run(
            ["docker", "compose", "logs", "sync", "--tail", "50"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return {
                "is_running": False,
                "error": "Cannot read sync logs"
            }

        logs = result.stdout

        # Парсим последнюю строку с прогрессом
        # Формат: [12998/26955] ##############................ 48.2% | 92.6 item/sec | ETA: 2.3min | Errors: 0 | Extra: 3 | MaxDepth: 6
        progress_pattern = r'\[(\d+)/(\d+)\].*?([\d.]+)%.*?([\d.]+) item/sec.*?ETA: ([\d.]+)min.*?Errors: (\d+).*?Extra: (\d+)'

        # Ищем последнее совпадение
        matches = list(re.finditer(progress_pattern, logs))

        if not matches:
            # Проверяем завершилась ли синхронизация
            if "EXPORT COMPLETED" in logs or "Sync completed" in logs:
                return {
                    "is_running": False,
                    "completed": True,
                    "message": "Synchronization completed"
                }

            # Проверяем началась ли синхронизация
            if "Starting dishes sync" in logs:
                return {
                    "is_running": True,
                    "progress": 0,
                    "message": "Starting synchronization..."
                }

            return {
                "is_running": False,
                "message": "No active synchronization"
            }

        # Берём последнее совпадение
        match = matches[-1]
        current = int(match.group(1))
        total = int(match.group(2))
        progress = float(match.group(3))
        speed = float(match.group(4))
        eta = float(match.group(5))
        errors = int(match.group(6))
        extra_labels = int(match.group(7))

        return {
            "is_running": True,
            "progress": progress,
            "current": current,
            "total": total,
            "speed": speed,
            "eta_minutes": eta,
            "errors": errors,
            "extra_labels": extra_labels
        }

    except subprocess.TimeoutExpired:
        return {
            "is_running": False,
            "error": "Timeout reading logs"
        }
    except Exception as e:
        return {
            "is_running": False,
            "error": str(e)
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
