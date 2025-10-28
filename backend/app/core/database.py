"""
Настройка SQLAlchemy и подключение к базе данных
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator

from app.core.config import settings

# ============================================================================
# SQLAlchemy Engine
# ============================================================================

# Создаём engine для основной БД
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Для SQLite
    echo=settings.DEBUG,  # Выводить SQL запросы в лог (только в dev)
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class для моделей
Base = declarative_base()


# ============================================================================
# Dependency для FastAPI
# ============================================================================

def get_db() -> Generator:
    """
    Dependency для получения database session в FastAPI endpoints

    Использование:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Инициализация БД
# ============================================================================

def init_db():
    """
    Создать все таблицы в БД
    Вызывается при первом запуске приложения
    """
    # Импортируем все модели, чтобы они были зарегистрированы
    from app.models import order, template, user, setting, table_filter  # noqa

    # Создаём таблицы
    Base.metadata.create_all(bind=engine)


# ============================================================================
# Dishes Database (мастер-база блюд - read-only)
# ============================================================================

import sqlite3
from typing import Optional, Dict, List


class DishesDB:
    """
    Подключение к dishes_full.sqlite (мастер-база блюд с иерархией)
    Read-only доступ
    """

    def __init__(self, db_path: str = None):
        # Используем новую БД с иерархией
        self.db_path = db_path or settings.DISHES_DB_PATH

    def get_connection(self) -> sqlite3.Connection:
        """Получить connection к dishes database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Возвращать результаты как dict
        return conn

    def get_dish_by_rk_code(self, rk_code: str, filters: Optional[Dict[str, List[str]]] = None) -> Optional[Dict]:
        """
        Получить блюдо по RKeeper коду с фильтрацией по подразделениям

        Args:
            rk_code: RKeeper код блюда
            filters: Фильтр по уровням иерархии, например:
                {
                    "level_1": ["01 Меню Британника"],
                    "level_2": ["Британника 1", "Британника 2"],
                    "level_3": ["Горячие блюда"]
                }

        Returns:
            {
                "rid": int,
                "name": str,
                "rkeeper_code": str,
                "weight_g": int,
                "protein": float,
                "fat": float,
                "carbs": float,
                "calories": int,
                "has_extra_labels": bool,
                "ingredients": [str],
                "extra_labels": [...]
            }
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Базовый запрос
        query = "SELECT * FROM dishes WHERE rkeeper_code = ?"
        params = [rk_code]

        # Добавляем фильтры по уровням иерархии
        if filters:
            for level_name, level_values in filters.items():
                if level_values:  # Если список не пустой
                    placeholders = ','.join('?' * len(level_values))
                    query += f" AND {level_name}_name IN ({placeholders})"
                    params.extend(level_values)

        query += " LIMIT 1"

        # Получаем основное блюдо
        cursor.execute(query, params)
        dish_row = cursor.fetchone()

        if not dish_row:
            conn.close()
            return None

        dish = dict(dish_row)

        # Получаем ингредиенты
        cursor.execute(
            "SELECT name FROM ingredients WHERE dish_rid = ?",
            (dish['rid'],)
        )
        dish['ingredients'] = [row['name'] for row in cursor.fetchall()]

        # Получаем дополнительные этикетки (если есть)
        dish['extra_labels'] = []
        if dish.get('has_extra_labels'):
            cursor.execute("""
                SELECT
                    extra_dish_rid,
                    extra_dish_name,
                    extra_dish_weight_g,
                    extra_dish_protein,
                    extra_dish_fat,
                    extra_dish_carbs,
                    extra_dish_calories
                FROM dish_extra_labels
                WHERE main_dish_rid = ?
                ORDER BY sort_order
            """, (dish['rid'],))

            dish['extra_labels'] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return dish

    def get_departments_tree(self, max_levels: int = 6) -> Dict:
        """
        Получить древовидную структуру подразделений

        Args:
            max_levels: Максимальное количество уровней (по умолчанию 6)

        Returns:
            {
                "level_1": [{"name": "...", "count": 123}, ...],
                "level_2": [{"name": "...", "count": 456}, ...],
                ...
            }
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        result = {}

        for level in range(1, max_levels + 1):
            level_name = f"level_{level}"
            query = f"""
                SELECT DISTINCT {level_name}_name AS name, COUNT(*) AS count
                FROM dishes
                WHERE {level_name}_name IS NOT NULL
                GROUP BY {level_name}_name
                ORDER BY {level_name}_name
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            result[level_name] = [{"name": row["name"], "count": row["count"]} for row in rows]

        conn.close()
        return result


# Глобальный экземпляр DishesDB
dishes_db = DishesDB()
