#!/usr/bin/env python3
"""
Инициализация базы данных
Создаёт таблицы и добавляет начальные данные
"""

import sys
from pathlib import Path

# Добавляем путь к app в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models import User, Setting, Template


def init_tables():
    """Создать все таблицы"""
    print("📊 Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы созданы")


def create_admin_user():
    """Создать admin пользователя"""
    db = SessionLocal()

    # Проверяем существует ли уже admin
    existing_admin = db.query(User).filter(User.login == "admin").first()
    if existing_admin:
        print("ℹ️  Admin пользователь уже существует")
        db.close()
        return

    # Создаём admin
    admin = User(
        login="admin",
        password_hash=hash_password("admin"),  # ВАЖНО: сменить в production!
        role="admin"
    )
    db.add(admin)
    db.commit()

    print("✅ Admin пользователь создан (admin/admin)")
    print("⚠️  ВАЖНО: Смените пароль после первого входа!")

    db.close()


def create_default_settings():
    """Создать начальные настройки"""
    db = SessionLocal()

    settings = [
        Setting(
            key="printer_ip",
            value="192.168.1.10",
            description="IP адрес принтера PC-365B"
        ),
        Setting(
            key="printer_port",
            value="9100",
            description="Порт принтера (TCP)"
        ),
        Setting(
            key="sh5_sync_last",
            value=None,
            description="Последняя синхронизация Store House 5"
        ),
        Setting(
            key="sh5_sync_error",
            value=None,
            description="Последняя ошибка синхронизации"
        ),
        Setting(
            key="archive_enabled",
            value="true",
            description="Включена ли автоархивация заказов"
        ),
    ]

    for setting in settings:
        existing = db.query(Setting).filter(Setting.key == setting.key).first()
        if not existing:
            db.add(setting)

    db.commit()
    print("✅ Начальные настройки созданы")
    db.close()


def create_default_template():
    """Создать шаблон по умолчанию"""
    db = SessionLocal()

    # Проверяем существует ли уже default шаблон
    existing = db.query(Template).filter(Template.is_default == True).first()
    if existing:
        print("ℹ️  Default шаблон уже существует")
        db.close()
        return

    # Создаём default шаблон
    default_template = Template(
        name="Britannica Default",
        brand_id="default",
        is_default=True,
        config={
            "paper_width_mm": 60,
            "paper_height_mm": 60,
            "paper_gap_mm": 2,
            "shelf_life_hours": 6,
            "logo": {
                "enabled": False,
                "path": None,
                "x": 5,
                "y": 5,
                "width": 50,
                "height": 20
            },
            "title": {
                "font": "3",
                "x": 10,
                "y": 30,
                "max_width": 200
            },
            "weight_calories": {
                "font": "2",
                "x": 10,
                "y": 60
            },
            "bju": {
                "enabled": True,
                "font": "2",
                "x": 10,
                "y": 80
            },
            "ingredients": {
                "enabled": True,
                "font": "1",
                "x": 10,
                "y": 100,
                "max_lines": 3
            },
            "datetime_shelf": {
                "font": "2",
                "x": 10,
                "y": 140
            },
            "barcode": {
                "type": "128",
                "x": 10,
                "y": 170,
                "height": 50,
                "narrow_bar": 2
            },
            "qr": {
                "enabled": False,
                "x": 200,
                "y": 170,
                "size": 4
            }
        }
    )

    db.add(default_template)
    db.commit()
    print("✅ Default шаблон создан")
    db.close()


def main():
    """Главная функция"""
    print("=" * 70)
    print("BRITANNICA LABELS - Инициализация базы данных")
    print("=" * 70)
    print()

    # 1. Создать таблицы
    init_tables()

    # 2. Создать admin пользователя
    create_admin_user()

    # 3. Создать начальные настройки
    create_default_settings()

    # 4. Создать default шаблон
    create_default_template()

    print()
    print("=" * 70)
    print("✅ Инициализация завершена!")
    print("=" * 70)
    print()
    print("Вы можете запустить сервер:")
    print("  cd backend")
    print("  python app/main.py")
    print()
    print("Логин: admin")
    print("Пароль: admin")
    print()


if __name__ == "__main__":
    main()
