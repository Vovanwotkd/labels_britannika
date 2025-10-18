"""
Модель шаблонов этикеток
"""

from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class Template(Base):
    """
    Шаблон этикетки (брендовый)
    """
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # "Britannica Pizza"
    brand_id = Column(String, unique=True, nullable=True, index=True)  # "britannica_pizza"
    is_default = Column(Boolean, default=False)  # Шаблон по умолчанию

    # Конфигурация шаблона (JSON)
    config = Column(JSON, nullable=False)
    # Пример:
    # {
    #   "paper_width_mm": 60,
    #   "paper_height_mm": 60,
    #   "paper_gap_mm": 2,
    #   "shelf_life_hours": 6,
    #   "logo": {"enabled": true, "path": "/logos/britannica.bmp", "x": 5, "y": 5},
    #   "title": {"font": "3", "x": 10, "y": 30},
    #   "weight_calories": {"font": "2", "x": 10, "y": 60},
    #   "bju": {"enabled": true, "font": "2", "x": 10, "y": 80},
    #   "ingredients": {"enabled": true, "font": "1", "x": 10, "y": 100, "max_lines": 3},
    #   "datetime_shelf": {"font": "2", "x": 10, "y": 140},
    #   "barcode": {"type": "128", "x": 10, "y": 170, "height": 50, "narrow_bar": 2}
    # }

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Template {self.name} (default={self.is_default})>"
