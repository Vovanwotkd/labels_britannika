"""
TSPL Renderer - генерация TSPL команд для принтера PC-365B
Формат: TSPL/TSPL2 (203 dpi)
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging
from app.services.printer.bitmap_renderer import BitmapRenderer

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
                Поддерживает новый формат с elements[] из визуального редактора
        """
        self.config = template_config
        self.dpi = 203  # PC-365B = 203 dpi
        self.mm_to_dots = 8  # 203 dpi ≈ 8 dots/mm

        # Проверяем формат конфигурации
        self.use_elements = "elements" in template_config

        # Настройки оптимизации BITMAP (можно переопределить в config)
        self.bitmap_width = template_config.get("bitmap_width", 280)  # оптимально для 58мм

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
        # Выбираем метод рендеринга в зависимости от формата конфигурации
        if self.use_elements:
            return self._render_with_elements(dish_data)
        else:
            return self._render_legacy(dish_data)

    def _render_with_elements(self, dish_data: Dict[str, Any]) -> str:
        """
        Рендеринг с использованием elements[] из визуального редактора

        Args:
            dish_data: Данные блюда

        Returns:
            TSPL команды
        """
        # Параметры бумаги
        width_mm = self.config.get("paper_width_mm", 58)
        height_mm = self.config.get("paper_height_mm", 60)
        gap_mm = self.config.get("paper_gap_mm", 2)

        # Даты
        from datetime import datetime, timedelta
        now = datetime.now()
        shelf_life_hours = self.config.get("shelf_life_hours", 6)
        shelf_life = now + timedelta(hours=shelf_life_hours)

        # Начинаем формировать TSPL
        tspl_commands = []

        # Заголовок
        tspl_commands.append(f"SIZE {width_mm} mm, {height_mm} mm")
        tspl_commands.append(f"GAP {gap_mm} mm, 0 mm")
        tspl_commands.append("DIRECTION 1")
        tspl_commands.append("CLS")

        # Обрабатываем элементы из редактора
        elements = self.config.get("elements", [])

        for element in elements:
            if not element.get("visible", True):
                continue  # Пропускаем невидимые элементы

            element_type = element.get("type")
            position = element.get("position", {})
            x_mm = position.get("x", 10)
            y_mm = position.get("y", 10)

            # Конвертируем мм в dots (203 dpi ≈ 8 dots/mm)
            x = int(x_mm * self.mm_to_dots)
            y = int(y_mm * self.mm_to_dots)

            font_size = element.get("fontSize", 14)

            # Генерируем BITMAP для каждого типа элемента
            if element_type == "text":
                # Текстовый блок (название, кастомный текст)
                field_name = element.get("fieldName")
                if field_name == "dish_name":
                    text = dish_data.get("name", "")
                else:
                    text = element.get("content", "")

                if text:
                    bitmap_cmd = BitmapRenderer.text_to_bitmap_tspl(
                        text=text,
                        x=x, y=y,
                        font_size=font_size,
                        width=self.bitmap_width
                    )
                    tspl_commands.append(bitmap_cmd)

            elif element_type == "weight":
                # Вес
                weight_g = dish_data.get("weight_g", 0)
                calories = dish_data.get("calories", 0)
                show_unit = element.get("showUnit", True)
                unit = "г" if show_unit else ""

                text = f"Вес: {weight_g}{unit}  Ккал: {calories}"
                bitmap_cmd = BitmapRenderer.text_to_bitmap_tspl(
                    text=text,
                    x=x, y=y,
                    font_size=font_size,
                    width=self.bitmap_width
                )
                tspl_commands.append(bitmap_cmd)

            elif element_type == "bju":
                # БЖУ
                protein = dish_data.get("protein", 0)
                fat = dish_data.get("fat", 0)
                carbs = dish_data.get("carbs", 0)

                parts = []
                if element.get("showProteins", True):
                    parts.append(f"Б:{protein:.0f}г")
                if element.get("showFats", True):
                    parts.append(f"Ж:{fat:.0f}г")
                if element.get("showCarbs", True):
                    parts.append(f"У:{carbs:.0f}г")

                text = " ".join(parts)
                bitmap_cmd = BitmapRenderer.text_to_bitmap_tspl(
                    text=text,
                    x=x, y=y,
                    font_size=font_size,
                    width=self.bitmap_width
                )
                tspl_commands.append(bitmap_cmd)

            elif element_type == "composition":
                # Состав
                ingredients = dish_data.get("ingredients", [])
                max_lines = element.get("maxLines", 3)

                if ingredients:
                    ingredients_text = ", ".join(ingredients[:max_lines])

                    # Ограничиваем длину
                    max_length = 50
                    if len(ingredients_text) > max_length:
                        ingredients_text = ingredients_text[:max_length-3] + "..."

                    text = f"Состав: {ingredients_text}"
                    bitmap_cmd = BitmapRenderer.text_to_bitmap_tspl(
                        text=text,
                        x=x, y=y,
                        font_size=font_size,
                        width=self.bitmap_width
                    )
                    tspl_commands.append(bitmap_cmd)

            elif element_type == "datetime":
                # Дата изготовления
                label = element.get("label", "Изготовлено:")
                date_format = element.get("format", "datetime")

                if date_format == "datetime":
                    date_str = now.strftime("%d.%m %H:%M")
                elif date_format == "date":
                    date_str = now.strftime("%d.%m.%Y")
                elif date_format == "time":
                    date_str = now.strftime("%H:%M")
                else:
                    date_str = now.strftime("%d.%m %H:%M")

                text = f"{label} {date_str}"
                bitmap_cmd = BitmapRenderer.text_to_bitmap_tspl(
                    text=text,
                    x=x, y=y,
                    font_size=font_size,
                    width=self.bitmap_width
                )
                tspl_commands.append(bitmap_cmd)

            elif element_type == "shelf_life":
                # Срок годности
                label = element.get("label", "Годен до:")
                hours = element.get("hours", shelf_life_hours)
                expiry = now + timedelta(hours=hours)

                date_str = expiry.strftime("%d.%m %H:%M")
                text = f"{label} {date_str}"
                bitmap_cmd = BitmapRenderer.text_to_bitmap_tspl(
                    text=text,
                    x=x, y=y,
                    font_size=font_size,
                    width=self.bitmap_width
                )
                tspl_commands.append(bitmap_cmd)

        # Команда печати
        tspl_commands.append("PRINT 1")

        # Объединяем команды
        tspl_data = "\n".join(tspl_commands)

        logger.debug(f"Generated TSPL for {dish_data['name']}: {len(tspl_data)} bytes")

        return tspl_data

    def _render_legacy(self, dish_data: Dict[str, Any]) -> str:
        """
        Старый метод рендеринга (для обратной совместимости)
        Используется если config не содержит elements[]

        Args:
            dish_data: Данные блюда

        Returns:
            TSPL команды
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
        # НАЗВАНИЕ БЛЮДА (используем BITMAP для кириллицы)
        # ====================================================================
        title_config = self.config.get("title", {})
        title_x = title_config.get("x", 10)
        title_y = title_config.get("y", 30)

        # Ограничиваем длину названия (чтобы поместилось)
        max_title_length = 25
        title_text = dish_data["name"]
        if len(title_text) > max_title_length:
            title_text = title_text[:max_title_length-3] + "..."

        # Рендерим в bitmap для поддержки кириллицы (ОПТИМИЗИРОВАНО)
        title_bitmap = BitmapRenderer.text_to_bitmap_tspl(
            text=title_text,
            x=title_x,
            y=title_y,
            font_size=20,  # Оптимизировано: было 24
            width=self.bitmap_width  # Оптимизировано: было 400
        )
        tspl_commands.append(title_bitmap)

        # ====================================================================
        # ВЕС И КАЛОРИИ (используем BITMAP для кириллицы)
        # ====================================================================
        wc_config = self.config.get("weight_calories", {})
        wc_x = wc_config.get("x", 10)
        wc_y = wc_config.get("y", 60)

        wc_text = f'Вес: {dish_data["weight_g"]}г | {dish_data["calories"]} ккал'
        wc_bitmap = BitmapRenderer.text_to_bitmap_tspl(
            text=wc_text,
            x=wc_x,
            y=wc_y,
            font_size=14,  # Оптимизировано: было 16
            width=self.bitmap_width
        )
        tspl_commands.append(wc_bitmap)

        # ====================================================================
        # БЖУ (если включено) (используем BITMAP для кириллицы)
        # ====================================================================
        bju_config = self.config.get("bju", {})
        if bju_config.get("enabled", True):
            bju_x = bju_config.get("x", 10)
            bju_y = bju_config.get("y", 80)

            bju_text = f'Б:{dish_data["protein"]:.0f}г Ж:{dish_data["fat"]:.0f}г У:{dish_data["carbs"]:.0f}г'
            bju_bitmap = BitmapRenderer.text_to_bitmap_tspl(
                text=bju_text,
                x=bju_x,
                y=bju_y,
                font_size=14,  # Оптимизировано: было 16
                width=self.bitmap_width
            )
            tspl_commands.append(bju_bitmap)

        # ====================================================================
        # СОСТАВ (если включено и есть ингредиенты) (используем BITMAP)
        # ====================================================================
        ing_config = self.config.get("ingredients", {})
        if ing_config.get("enabled", True) and dish_data.get("ingredients"):
            ing_x = ing_config.get("x", 10)
            ing_y = ing_config.get("y", 100)
            max_lines = ing_config.get("max_lines", 3)

            # Объединяем ингредиенты
            ingredients_text = ", ".join(dish_data["ingredients"][:max_lines])

            # Ограничиваем длину
            max_ing_length = 50
            if len(ingredients_text) > max_ing_length:
                ingredients_text = ingredients_text[:max_ing_length-3] + "..."

            ing_bitmap = BitmapRenderer.text_to_bitmap_tspl(
                text=f"Состав: {ingredients_text}",
                x=ing_x,
                y=ing_y,
                font_size=12,  # Оптимизировано: было 14
                width=self.bitmap_width
            )
            tspl_commands.append(ing_bitmap)

        # ====================================================================
        # ДАТА ПЕЧАТИ И СРОК ГОДНОСТИ (используем BITMAP)
        # ====================================================================
        dt_config = self.config.get("datetime_shelf", {})
        dt_x = dt_config.get("x", 10)
        dt_y = dt_config.get("y", 140)

        date_str = now.strftime("%d.%m %H:%M")
        shelf_str = shelf_life.strftime("%d.%m %H:%M")

        date_bitmap = BitmapRenderer.text_to_bitmap_tspl(
            text=f"Изготовлено: {date_str}",
            x=dt_x,
            y=dt_y,
            font_size=12,  # Оптимизировано: было 16
            width=self.bitmap_width
        )
        tspl_commands.append(date_bitmap)

        shelf_bitmap = BitmapRenderer.text_to_bitmap_tspl(
            text=f"Годен до: {shelf_str}",
            x=dt_x,
            y=dt_y + 20,
            font_size=12,  # Оптимизировано: было 16
            width=self.bitmap_width
        )
        tspl_commands.append(shelf_bitmap)

        # ====================================================================
        # ШТРИХ-КОД И QR-КОД - УДАЛЕНЫ (оптимизация размера)
        # ====================================================================
        # Штрих-код и QR-код убраны для экономии места на этикетке
        # и уменьшения размера TSPL данных

        # ====================================================================
        # ПЕЧАТЬ
        # ====================================================================
        tspl_commands.append("PRINT 1")  # Напечатать 1 экземпляр

        # Объединяем все команды
        tspl_data = "\n".join(tspl_commands)

        logger.debug(f"Generated TSPL (legacy) for {dish_data['name']}: {len(tspl_data)} bytes")

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
