"""
Модель фильтра столов
"""

from sqlalchemy import Column, String, Boolean

from app.core.database import Base


class TableFilter(Base):
    """
    Фильтр столов (какие столы отслеживаем)
    """
    __tablename__ = "table_filter"

    table_code = Column(String, primary_key=True)  # Код стола (141, 142, ...)
    table_name = Column(String, nullable=True)  # Название стола
    zone = Column(String, nullable=True)  # Зона (Kitchen, Bar, Hall)
    enabled = Column(Boolean, default=True)  # Отслеживать этот стол?

    def __repr__(self):
        return f"<TableFilter {self.table_code} ({self.zone}) - {'✓' if self.enabled else '✗'}>"
