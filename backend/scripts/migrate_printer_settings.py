"""
Migration: Добавление настроек для CUPS печати

Добавляет новые поля:
- printer_type: "tcp" или "cups"
- printer_name: имя CUPS принтера (для type="cups")

Старые поля (printer_ip, printer_port) сохраняются для обратной совместимости (type="tcp")
"""

import sys
import os

# Добавляем путь к app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.models import Setting
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Выполнить миграцию"""
    db = SessionLocal()

    try:
        logger.info("🔄 Начало миграции printer settings...")

        # Проверяем существует ли уже printer_type
        existing_type = db.query(Setting).filter(Setting.key == "printer_type").first()

        if existing_type:
            logger.info("⏭️  printer_type уже существует, миграция не требуется")
            return

        # Добавляем printer_type (по умолчанию "tcp" для обратной совместимости)
        printer_type = Setting(
            key="printer_type",
            value="tcp",
            description="Тип подключения к принтеру: 'tcp' (raw TSPL) или 'cups' (драйвер)"
        )
        db.add(printer_type)

        # Добавляем printer_name (пустой по умолчанию, используется только для CUPS)
        printer_name = Setting(
            key="printer_name",
            value="",
            description="Имя CUPS принтера (используется только если printer_type=cups)"
        )
        db.add(printer_name)

        db.commit()

        logger.info("✅ Миграция выполнена успешно!")
        logger.info("   Добавлено:")
        logger.info("   - printer_type = 'tcp'")
        logger.info("   - printer_name = ''")
        logger.info("")
        logger.info("   Существующие настройки (printer_ip, printer_port) сохранены")

    except Exception as e:
        logger.error(f"❌ Ошибка миграции: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
    print("\nГотово! Перезапустите backend чтобы применить изменения.")
