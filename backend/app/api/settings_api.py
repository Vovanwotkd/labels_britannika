"""
Settings API
Управление настройками системы
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Setting, TableFilter
from app.api.auth_api import require_auth, require_admin
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ============================================================================
# SCHEMAS
# ============================================================================

class SettingSchema(BaseModel):
    """Схема настройки"""
    key: str
    value: str
    description: Optional[str]

    class Config:
        from_attributes = True


class SettingUpdateRequest(BaseModel):
    """Запрос на обновление настройки"""
    key: str
    value: str


class TableFilterSchema(BaseModel):
    """Схема фильтра столов"""
    id: int
    filter_type: str  # "include" или "exclude"
    table_codes: List[str]
    is_active: bool
    description: Optional[str]

    class Config:
        from_attributes = True


class TableFilterCreateRequest(BaseModel):
    """Запрос на создание фильтра столов"""
    filter_type: str  # "include" или "exclude"
    table_codes: List[str]
    is_active: bool = True
    description: Optional[str] = None


class TableFilterUpdateRequest(BaseModel):
    """Запрос на обновление фильтра столов"""
    filter_type: Optional[str] = None
    table_codes: Optional[List[str]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


# ============================================================================
# SETTINGS ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[SettingSchema])
async def get_all_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Получить все настройки

    Требует аутентификации
    """
    settings = db.query(Setting).all()
    return settings


@router.get("/{key}", response_model=SettingSchema)
async def get_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Получить настройку по ключу

    Требует аутентификации
    """
    setting = db.query(Setting).filter(Setting.key == key).first()

    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    return setting


@router.put("/")
async def update_setting(
    request: SettingUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Обновить настройку

    Требует прав администратора
    """
    setting = db.query(Setting).filter(Setting.key == request.key).first()

    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{request.key}' not found")

    setting.value = request.value
    db.commit()

    logger.info(f"⚙️  Setting updated: {request.key} = {request.value}")

    return {
        "success": True,
        "message": f"Setting '{request.key}' updated",
        "setting": SettingSchema.from_orm(setting)
    }


@router.post("/batch")
async def update_settings_batch(
    settings: List[SettingUpdateRequest],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Массовое обновление настроек

    Требует прав администратора
    """
    updated_count = 0

    for setting_update in settings:
        setting = db.query(Setting).filter(Setting.key == setting_update.key).first()

        if setting:
            setting.value = setting_update.value
            updated_count += 1
        else:
            logger.warning(f"⚠️  Setting '{setting_update.key}' not found, skipping")

    db.commit()

    logger.info(f"⚙️  Batch update: {updated_count} settings updated")

    return {
        "success": True,
        "message": f"Updated {updated_count} settings",
        "updated_count": updated_count
    }


# ============================================================================
# TABLE FILTERS ENDPOINTS
# ============================================================================

@router.get("/filters/", response_model=List[TableFilterSchema])
async def get_table_filters(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Получить все фильтры столов

    Требует аутентификации
    """
    filters = db.query(TableFilter).all()
    return filters


@router.get("/filters/{filter_id}", response_model=TableFilterSchema)
async def get_table_filter(
    filter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Получить фильтр столов по ID

    Требует аутентификации
    """
    filter_obj = db.query(TableFilter).filter(TableFilter.id == filter_id).first()

    if not filter_obj:
        raise HTTPException(status_code=404, detail="Table filter not found")

    return filter_obj


@router.post("/filters/", response_model=TableFilterSchema)
async def create_table_filter(
    request: TableFilterCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Создать фильтр столов

    Требует прав администратора

    Типы фильтров:
    - "include": Обрабатывать только указанные столы
    - "exclude": Пропускать указанные столы
    """
    if request.filter_type not in ["include", "exclude"]:
        raise HTTPException(
            status_code=400,
            detail="filter_type must be 'include' or 'exclude'"
        )

    filter_obj = TableFilter(
        filter_type=request.filter_type,
        table_codes=request.table_codes,
        is_active=request.is_active,
        description=request.description,
    )

    db.add(filter_obj)
    db.commit()
    db.refresh(filter_obj)

    logger.info(
        f"➕ Table filter created: type={request.filter_type}, "
        f"codes={request.table_codes}, active={request.is_active}"
    )

    return filter_obj


@router.put("/filters/{filter_id}", response_model=TableFilterSchema)
async def update_table_filter(
    filter_id: int,
    request: TableFilterUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Обновить фильтр столов

    Требует прав администратора
    """
    filter_obj = db.query(TableFilter).filter(TableFilter.id == filter_id).first()

    if not filter_obj:
        raise HTTPException(status_code=404, detail="Table filter not found")

    # Обновляем поля
    if request.filter_type is not None:
        if request.filter_type not in ["include", "exclude"]:
            raise HTTPException(
                status_code=400,
                detail="filter_type must be 'include' or 'exclude'"
            )
        filter_obj.filter_type = request.filter_type

    if request.table_codes is not None:
        filter_obj.table_codes = request.table_codes

    if request.is_active is not None:
        filter_obj.is_active = request.is_active

    if request.description is not None:
        filter_obj.description = request.description

    db.commit()
    db.refresh(filter_obj)

    logger.info(f"📝 Table filter updated: id={filter_id}")

    return filter_obj


@router.delete("/filters/{filter_id}")
async def delete_table_filter(
    filter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Удалить фильтр столов

    Требует прав администратора
    """
    filter_obj = db.query(TableFilter).filter(TableFilter.id == filter_id).first()

    if not filter_obj:
        raise HTTPException(status_code=404, detail="Table filter not found")

    db.delete(filter_obj)
    db.commit()

    logger.info(f"🗑️  Table filter deleted: id={filter_id}")

    return {
        "success": True,
        "message": f"Table filter #{filter_id} deleted"
    }


# ============================================================================
# SYSTEM INFO
# ============================================================================

@router.get("/system/info")
async def get_system_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Получить информацию о системе

    Требует аутентификации
    """
    from app.core.config import settings
    from app.services.websocket.manager import manager

    # Статистика БД
    from app.models import Order, OrderItem, PrintJob

    orders_count = db.query(Order).count()
    items_count = db.query(OrderItem).count()
    jobs_total = db.query(PrintJob).count()
    jobs_queued = db.query(PrintJob).filter(PrintJob.status == "QUEUED").count()
    jobs_printing = db.query(PrintJob).filter(PrintJob.status == "PRINTING").count()
    jobs_done = db.query(PrintJob).filter(PrintJob.status == "DONE").count()
    jobs_failed = db.query(PrintJob).filter(PrintJob.status == "FAILED").count()

    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timezone": settings.TIMEZONE,
        "printer": {
            "ip": settings.PRINTER_IP,
            "port": settings.PRINTER_PORT,
        },
        "database": {
            "orders": orders_count,
            "order_items": items_count,
            "print_jobs": {
                "total": jobs_total,
                "queued": jobs_queued,
                "printing": jobs_printing,
                "done": jobs_done,
                "failed": jobs_failed,
            }
        },
        "websocket": {
            "connections": manager.get_connections_count(),
            "rooms": {
                "orders": manager.get_room_size("orders"),
            }
        }
    }
