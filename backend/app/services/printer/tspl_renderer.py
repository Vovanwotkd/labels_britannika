"""
TSPL Renderer - генерация TSPL команд для принтера PC-365B
Формат: TSPL/TSPL2 (203 dpi)
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TSPLRenderer:
    """
    Генератор TSPL команд для термопринтера PC-365B / XP-D365B

    Спецификация:
    - DPI: 203 (≈ 8 точек/мм)
    - Язык: TSPL/TSPL2
    - Порт: TCP 9100
    """

    def __init__(self, template_config: Dict[str, Any]):
        """
        Args:
            template_config: Конфигурация шаблона (из Template.config)
        """
        self.config = template_config
        self.dpi = 203  # PC-365B = 203 dpi
        self.mm_to_dots = 8  # 203 dpi ≈ 8 dots/mm

    def render(self, dish_data: Dict[str, Any]) -> str:
        """
        Генерирует TSPL команды для печати этикетки

        Args:
            dish_data: {
                "name": str,              # Название блюда
                "rk_code": str,           # RKeeper код
                "weight_g": int,          # Вес (грамм)
                "calories": int,          # Калории
                "protein": float,         # Белки (г)
                "fat": float,             # Жиры (г)
                "carbs": float,           # Углеводы (г)
                "ingredients": [str],     # Состав
                "label_type": str,        # MAIN | EXTRA
            }

        Returns:
            TSPL команды (строка)
        """

        # Параметры из конфигурации
        width_mm = self.config.get("paper_width_mm", 60)
        height_mm = self.config.get("paper_height_mm", 60)
        gap_mm = self.config.get("paper_gap_mm", 2)
        shelf_life_hours = self.config.get("shelf_life_hours", 6)

        # Даты
        now = datetime.now()
        shelf_life = now + timedelta(hours=shelf_life_hours)

        # Начинаем формировать TSPL
        tspl_commands = []

        # ====================================================================
        # ЗАГОЛОВОК (настройки бумаги)
        # ====================================================================
        tspl_commands.append(f"SIZE {width_mm} mm, {height_mm} mm")
        tspl_commands.append(f"GAP {gap_mm} mm, 0 mm")
        tspl_commands.append("DIRECTION 1")  # Ориентация
        tspl_commands.append("CLS")  # Очистить буфер

        # ====================================================================
        # ЛОГОТИП (если включен)
        # ====================================================================
        logo_config = self.config.get("logo", {})
        if logo_config.get("enabled") and logo_config.get("path"):
            # TODO: Реализовать загрузку и конвертацию BMP
            # tspl_commands.append(f'BITMAP {logo_config["x"]},{logo_config["y"]},"{logo_config["path"]}"')
            pass

        # ====================================================================
        # НАЗВАНИЕ БЛЮДА
        # ====================================================================
        title_config = self.config.get("title", {})
        title_font = title_config.get("font", "3")
        title_x = title_config.get("x", 10)
        title_y = title_config.get("y", 30)

        # Ограничиваем длину названия (чтобы поместилось)
        max_title_length = 25
        title_text = dish_data["name"]
        if len(title_text) > max_title_length:
            title_text = title_text[:max_title_length-3] + "..."

        tspl_commands.append(
            f'TEXT {title_x},{title_y},"{title_font}",0,1,1,"{self._escape_text(title_text)}"'
        )

        # ====================================================================
        # ВЕС И КАЛОРИИ
        # ====================================================================
        wc_config = self.config.get("weight_calories", {})
        wc_font = wc_config.get("font", "2")
        wc_x = wc_config.get("x", 10)
        wc_y = wc_config.get("y", 60)

        wc_text = f'Вес: {dish_data["weight_g"]}г | {dish_data["calories"]} ккал'
        tspl_commands.append(
            f'TEXT {wc_x},{wc_y},"{wc_font}",0,1,1,"{self._escape_text(wc_text)}"'
        )

        # ====================================================================
        # БЖУ (если включено)
        # ====================================================================
        bju_config = self.config.get("bju", {})
        if bju_config.get("enabled", True):
            bju_font = bju_config.get("font", "2")
            bju_x = bju_config.get("x", 10)
            bju_y = bju_config.get("y", 80)

            bju_text = f'Б:{dish_data["protein"]:.0f}г Ж:{dish_data["fat"]:.0f}г У:{dish_data["carbs"]:.0f}г'
            tspl_commands.append(
                f'TEXT {bju_x},{bju_y},"{bju_font}",0,1,1,"{self._escape_text(bju_text)}"'
            )

        # ====================================================================
        # СОСТАВ (если включено и есть ингредиенты)
        # ====================================================================
        ing_config = self.config.get("ingredients", {})
        if ing_config.get("enabled", True) and dish_data.get("ingredients"):
            ing_font = ing_config.get("font", "1")
            ing_x = ing_config.get("x", 10)
            ing_y = ing_config.get("y", 100)
            max_lines = ing_config.get("max_lines", 3)

            # Объединяем ингредиенты
            ingredients_text = ", ".join(dish_data["ingredients"][:max_lines])

            # Ограничиваем длину
            max_ing_length = 50
            if len(ingredients_text) > max_ing_length:
                ingredients_text = ingredients_text[:max_ing_length-3] + "..."

            tspl_commands.append(
                f'TEXT {ing_x},{ing_y},"{ing_font}",0,1,1,"Состав: {self._escape_text(ingredients_text)}"'
            )

        # ====================================================================
        # ДАТА ПЕЧАТИ И СРОК ГОДНОСТИ
        # ====================================================================
        dt_config = self.config.get("datetime_shelf", {})
        dt_font = dt_config.get("font", "2")
        dt_x = dt_config.get("x", 10)
        dt_y = dt_config.get("y", 140)

        date_str = now.strftime("%d.%m %H:%M")
        shelf_str = shelf_life.strftime("%d.%m %H:%M")

        tspl_commands.append(
            f'TEXT {dt_x},{dt_y},"{dt_font}",0,1,1,"Изготовлено: {date_str}"'
        )
        tspl_commands.append(
            f'TEXT {dt_x},{dt_y + 20},"{dt_font}",0,1,1,"Годен до: {shelf_str}"'
        )

        # ====================================================================
        # ШТРИХ-КОД
        # ====================================================================
        bc_config = self.config.get("barcode", {})
        bc_type = bc_config.get("type", "128")  # CODE128
        bc_x = bc_config.get("x", 10)
        bc_y = bc_config.get("y", 180)
        bc_height = bc_config.get("height", 50)
        bc_narrow = bc_config.get("narrow_bar", 2)

        tspl_commands.append(
            f'BARCODE {bc_x},{bc_y},"{bc_type}",{bc_height},1,0,{bc_narrow},{bc_narrow},"{dish_data["rk_code"]}"'
        )

        # ====================================================================
        # QR-КОД (если включен)
        # ====================================================================
        qr_config = self.config.get("qr", {})
        if qr_config.get("enabled", False):
            qr_x = qr_config.get("x", 200)
            qr_y = qr_config.get("y", 170)
            qr_size = qr_config.get("size", 4)

            # QR код содержит RK код блюда
            tspl_commands.append(
                f'QRCODE {qr_x},{qr_y},L,{qr_size},A,0,"{dish_data["rk_code"]}"'
            )

        # ====================================================================
        # ПЕЧАТЬ
        # ====================================================================
        tspl_commands.append("PRINT 1")  # Напечатать 1 экземпляр

        # Объединяем все команды
        tspl_data = "\n".join(tspl_commands)

        logger.debug(f"Generated TSPL for {dish_data['name']} ({dish_data['rk_code']})")

        return tspl_data

    def _escape_text(self, text: str) -> str:
        """
        Экранирование текста для TSPL
        Удаляет спецсимволы, которые могут сломать команды

        Args:
            text: Исходный текст

        Returns:
            Экранированный текст
        """
        # TSPL использует кавычки для строк, нужно их экранировать
        text = text.replace('"', "'")  # Заменяем двойные кавычки на одинарные
        text = text.replace('\n', ' ')  # Убираем переносы строк
        text = text.replace('\r', '')   # Убираем возврат каретки

        return text

    def render_test_label(self) -> str:
        """
        Генерирует тестовую этикетку для проверки принтера

        Returns:
            TSPL команды для тестовой этикетки
        """
        test_data = {
            "name": "ТЕСТОВАЯ ЭТИКЕТКА",
            "rk_code": "TEST123",
            "weight_g": 100,
            "calories": 250,
            "protein": 10.0,
            "fat": 5.0,
            "carbs": 30.0,
            "ingredients": ["Тест", "Проверка", "Принтер"],
            "label_type": "MAIN"
        }

        return self.render(test_data)


# ============================================================================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# ============================================================================

def example_usage():
    """Пример использования TSPLRenderer"""

    # Конфигурация шаблона (из Template.config)
    template_config = {
        "paper_width_mm": 60,
        "paper_height_mm": 60,
        "paper_gap_mm": 2,
        "shelf_life_hours": 6,
        "logo": {"enabled": False},
        "title": {"font": "3", "x": 10, "y": 30},
        "weight_calories": {"font": "2", "x": 10, "y": 60},
        "bju": {"enabled": True, "font": "2", "x": 10, "y": 80},
        "ingredients": {"enabled": True, "font": "1", "x": 10, "y": 100, "max_lines": 3},
        "datetime_shelf": {"font": "2", "x": 10, "y": 140},
        "barcode": {"type": "128", "x": 10, "y": 180, "height": 50, "narrow_bar": 2},
        "qr": {"enabled": False}
    }

    # Данные блюда
    dish_data = {
        "name": "Лепешка с говядиной",
        "rk_code": "2538",
        "weight_g": 259,
        "calories": 380,
        "protein": 25.0,
        "fat": 15.0,
        "carbs": 40.0,
        "ingredients": ["говядина", "тесто", "лук", "специи"],
        "label_type": "MAIN"
    }

    # Генерируем TSPL
    renderer = TSPLRenderer(template_config)
    tspl = renderer.render(dish_data)

    print("=" * 70)
    print("TSPL КОМАНДЫ:")
    print("=" * 70)
    print(tspl)
    print("=" * 70)


if __name__ == "__main__":
    example_usage()
