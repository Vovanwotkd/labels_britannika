"""
Print Service - высокоуровневый API для печати
Объединяет TSPLRenderer + TCPClient + работу с БД
"""

import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import dishes_db
from app.models import Template, PrintJob, Order, OrderItem
from app.services.printer.tspl_renderer import TSPLRenderer
from app.services.printer.tcp_client import PrinterClient

logger = logging.getLogger(__name__)


class PrintService:
    """
    Сервис печати этикеток

    Основные методы:
    - print_by_rk_code() - печать по RKeeper коду
    - print_order() - печать всего заказа
    - print_order_item() - печать конкретного блюда из заказа
    - test_print() - тестовая печать
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Database session
        """
        self.db = db
        self.printer = PrinterClient(
            host=settings.PRINTER_IP,
            port=settings.PRINTER_PORT,
            timeout=settings.PRINTER_TIMEOUT
        )

    def _get_default_template(self) -> Template:
        """
        Получить шаблон по умолчанию

        Returns:
            Template объект
        """
        template = self.db.query(Template).filter(
            Template.is_default == True
        ).first()

        if not template:
            raise ValueError("Default шаблон не найден. Запустите scripts/init_db.py")

        return template

    def _get_dish_data(self, rk_code: str) -> Optional[Dict]:
        """
        Получить данные блюда из dishes_with_extras.sqlite

        Args:
            rk_code: RKeeper код блюда

        Returns:
            Dict с данными блюда или None
        """
        dish = dishes_db.get_dish_by_rk_code(rk_code)

        if not dish:
            logger.warning(f"Блюдо с RK кодом {rk_code} не найдено в базе")
            return None

        return dish

    def print_by_rk_code(self, rk_code: str, quantity: int = 1) -> dict:
        """
        Печать этикеток по RKeeper коду

        ВАЖНО: Эта функция НЕ печатает напрямую!
        Она создаёт PrintJob записи в БД, которые обрабатывает PrintQueueWorker

        Args:
            rk_code: RKeeper код блюда
            quantity: Количество порций

        Returns:
            {
                "success": bool,
                "queued": int,  # Количество заданий добавлено в очередь
                "message": str
            }
        """
        # Получаем данные блюда
        dish = self._get_dish_data(rk_code)
        if not dish:
            return {
                "success": False,
                "queued": 0,
                "message": f"Блюдо {rk_code} не найдено"
            }

        # Получаем шаблон
        template = self._get_default_template()
        renderer = TSPLRenderer(template.config)

        # Счётчик созданных заданий
        queued_count = 0

        # Создаём задания для основных этикеток (по количеству порций)
        for i in range(quantity):
            tspl = renderer.render({
                "name": dish["name"],
                "rk_code": dish["rkeeper_code"],
                "weight_g": dish["weight_g"],
                "calories": dish["calories"],
                "protein": dish["protein"],
                "fat": dish["fat"],
                "carbs": dish["carbs"],
                "ingredients": dish["ingredients"],
                "label_type": "MAIN"
            })

            # Создаём PrintJob (без привязки к order_item_id, т.к. это прямая печать)
            job = PrintJob(
                order_item_id=None,  # Прямая печать, без заказа
                tspl_data=tspl,
                status="QUEUED",
                retry_count=0,
                max_retries=3
            )
            self.db.add(job)
            queued_count += 1

        # Создаём задания для дополнительных этикеток (если есть)
        if dish.get("has_extra_labels") and dish.get("extra_labels"):
            for extra in dish["extra_labels"]:
                for i in range(quantity):
                    tspl = renderer.render({
                        "name": extra["extra_dish_name"],
                        "rk_code": dish["rkeeper_code"],  # Используем код основного блюда
                        "weight_g": extra["extra_dish_weight_g"],
                        "calories": extra["extra_dish_calories"],
                        "protein": extra.get("extra_dish_protein", 0),
                        "fat": extra.get("extra_dish_fat", 0),
                        "carbs": extra.get("extra_dish_carbs", 0),
                        "ingredients": [],  # Доп. этикетки без состава
                        "label_type": "EXTRA"
                    })

                    job = PrintJob(
                        order_item_id=None,
                        tspl_data=tspl,
                        status="QUEUED",
                        retry_count=0,
                        max_retries=3
                    )
                    self.db.add(job)
                    queued_count += 1

        # Сохраняем все задания
        self.db.commit()

        logger.info(f"✅ Создано {queued_count} заданий печати для {rk_code}")

        return {
            "success": True,
            "queued": queued_count,
            "message": f"В очередь добавлено {queued_count} этикеток"
        }

    def test_print(self) -> dict:
        """
        Тестовая печать (проверка принтера)

        Returns:
            {
                "success": bool,
                "message": str
            }
        """
        # Проверяем доступность принтера
        if not self.printer.test_connection():
            return {
                "success": False,
                "message": f"Принтер {settings.PRINTER_IP}:{settings.PRINTER_PORT} недоступен"
            }

        # Получаем шаблон
        try:
            template = self._get_default_template()
        except ValueError as e:
            return {
                "success": False,
                "message": str(e)
            }

        # Генерируем тестовую этикетку
        renderer = TSPLRenderer(template.config)
        tspl = renderer.render_test_label()

        # Отправляем на печать
        success = self.printer.send(tspl)

        return {
            "success": success,
            "message": "Тестовая этикетка напечатана" if success else "Ошибка печати"
        }

    def get_printer_status(self) -> dict:
        """
        Получить статус принтера

        Returns:
            {
                "online": bool,
                "host": str,
                "port": int,
                "error": Optional[str]
            }
        """
        return self.printer.get_status()
