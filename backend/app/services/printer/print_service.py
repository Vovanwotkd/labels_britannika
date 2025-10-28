"""
Print Service - высокоуровневый API для печати
Объединяет TSPLRenderer + TCPClient + работу с БД
"""

import logging
import json
from typing import Dict, Optional, List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import dishes_db
from app.models import Template, PrintJob, Order, OrderItem, Setting
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
        Получить шаблон по умолчанию (для основных блюд)

        Returns:
            Template объект
        """
        template = self.db.query(Template).filter(
            Template.is_default == True
        ).first()

        if not template:
            raise ValueError("Default шаблон не найден. Запустите scripts/init_db.py")

        return template

    def _get_extra_template(self) -> Template:
        """
        Получить шаблон для дополнительных этикеток

        Returns:
            Template объект
        """
        # Пытаемся получить шаблон из настроек
        extra_template_setting = self.db.query(Setting).filter(
            Setting.key == "default_extra_template_id"
        ).first()

        if extra_template_setting and extra_template_setting.value:
            try:
                template_id = int(extra_template_setting.value)
                template = self.db.query(Template).filter(Template.id == template_id).first()
                if template:
                    return template
            except (ValueError, TypeError):
                pass

        # Если не настроен, используем основной шаблон
        logger.debug("Шаблон для доп. этикеток не настроен, используем основной")
        return self._get_default_template()

    def _get_selected_departments(self) -> Optional[Dict[str, List[str]]]:
        """
        Получить выбранные подразделения из настроек

        Returns:
            Dict с фильтрами или None
            Пример: {"level_1": ["01 Меню Британника"], "level_2": ["Британника 1"]}
        """
        setting = self.db.query(Setting).filter(
            Setting.key == "selected_departments"
        ).first()

        if not setting or not setting.value:
            return None

        try:
            filters = json.loads(setting.value)
            # Фильтруем пустые списки
            return {k: v for k, v in filters.items() if v}
        except (json.JSONDecodeError, TypeError):
            logger.warning("Не удалось распарсить selected_departments")
            return None

    def _get_dish_data(self, rk_code: str) -> Optional[Dict]:
        """
        Получить данные блюда из dishes_full.sqlite с учётом фильтров

        Args:
            rk_code: RKeeper код блюда

        Returns:
            Dict с данными блюда или None
        """
        # Получаем фильтры по подразделениям
        filters = self._get_selected_departments()

        # Получаем блюдо с фильтрацией
        dish = dishes_db.get_dish_by_rk_code(rk_code, filters)

        if not dish:
            logger.warning(
                f"Блюдо с RK кодом {rk_code} не найдено "
                f"{'с учётом фильтров подразделений' if filters else 'в базе'}"
            )
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

        # Получаем шаблоны (основной и для доп. этикеток)
        main_template = self._get_default_template()
        extra_template = self._get_extra_template()

        main_renderer = TSPLRenderer(main_template.config)
        extra_renderer = TSPLRenderer(extra_template.config)

        # Счётчик созданных заданий
        queued_count = 0

        # Создаём задания для основных этикеток (по количеству порций)
        for i in range(quantity):
            tspl = main_renderer.render({
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
                    # ИСПОЛЬЗУЕМ EXTRA_RENDERER для дополнительных этикеток
                    tspl = extra_renderer.render({
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
