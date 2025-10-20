"""
RKeeper API Routes
Эндпоинты для работы с RKeeper
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..services.rkeeper_client import get_rkeeper_client, RKeeperClient
from ..api.auth_api import require_auth, require_admin
from ..core.database import get_db
from ..models.user import User
from ..models.table_filter import TableFilter

router = APIRouter(prefix="/api/rkeeper", tags=["rkeeper"])


# ============================================================================
# SCHEMAS
# ============================================================================

class SaveTablesRequest(BaseModel):
    """Запрос на сохранение выбранных столов"""
    tables: List[Dict[str, str]]  # [{"code": "1", "name": "Киоск"}, ...]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/tables")
async def get_tables(
    current_user: User = Depends(require_auth)
) -> List[Dict[str, str]]:
    """
    Получает список активных столов из RKeeper

    Returns:
        Список столов с полями: ident, code, name, status, hall
    """
    try:
        client = get_rkeeper_client()
        tables = await client.get_tables()
        return tables
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch tables from RKeeper: {str(e)}"
        )


@router.post("/tables/save")
async def save_selected_tables(
    request: SaveTablesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Сохраняет выбранные столы в базу данных
    Удаляет все существующие записи и создаёт новые

    Требует прав администратора
    """
    try:
        # Удаляем все существующие фильтры столов
        db.query(TableFilter).delete()

        # Добавляем новые выбранные столы
        for table in request.tables:
            table_filter = TableFilter(
                table_code=table.get("code", ""),
                table_name=table.get("name", ""),
                zone=None,  # Пока не используем зоны
                enabled=True
            )
            db.add(table_filter)

        db.commit()

        return {
            "success": True,
            "message": f"Saved {len(request.tables)} tables",
            "count": len(request.tables)
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save tables: {str(e)}"
        )


@router.get("/tables/selected")
async def get_selected_tables(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
) -> List[Dict[str, str]]:
    """
    Получает список выбранных столов из базы данных

    Returns:
        Список выбранных столов
    """
    filters = db.query(TableFilter).filter(TableFilter.enabled == True).all()

    return [
        {
            "code": f.table_code,
            "name": f.table_name or f.table_code
        }
        for f in filters
    ]
