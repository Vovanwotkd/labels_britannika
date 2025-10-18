"""
Модель настроек системы
"""

from sqlalchemy import Column, String, Text

from app.core.database import Base


class Setting(Base):
    """
    Настройки системы (key-value хранилище)
    """
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Setting {self.key}={self.value[:20] if self.value else None}>"
