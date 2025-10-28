"""
API для работы с подразделениями (departments)
"""

from typing import Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db, dishes_db
from app.api.auth_api import get_current_user
from app.models import User

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.get("/tree")
async def get_departments_tree(
    current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Получить древовидную структуру подразделений

    Returns:
        {
            "level_1": [{"name": "01 Меню Британника", "count": 5234}, ...],
            "level_2": [{"name": "Британника 1", "count": 2456}, ...],
            ...
        }
    """
    try:
        tree = dishes_db.get_departments_tree()
        return tree
    except Exception as e:
        # Если БД ещё не синхронизирована, возвращаем пустую структуру
        return {
            "level_1": [],
            "level_2": [],
            "level_3": [],
            "level_4": [],
            "level_5": [],
            "level_6": [],
            "error": str(e)
        }
