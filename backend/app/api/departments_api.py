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
    Получить иерархическую структуру подразделений

    Returns:
        {
            "tree": [
                {
                    "name": "01 Меню Британника",
                    "count": 5764,
                    "level": 1,
                    "children": [
                        {
                            "name": "Британника 1",
                            "count": 1200,
                            "level": 2,
                            "children": [...]
                        }
                    ]
                }
            ]
        }
    """
    try:
        tree = dishes_db.get_departments_tree()
        return tree
    except Exception as e:
        # Если БД ещё не синхронизирована, возвращаем пустую структуру
        return {
            "tree": [],
            "error": str(e)
        }
