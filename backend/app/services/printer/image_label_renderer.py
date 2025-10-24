"""
Image Label Renderer - генерация PNG этикеток для CUPS печати
"""

from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any
from datetime import datetime, timedelta
import io
import logging

logger = logging.getLogger(__name__)


class ImageLabelRenderer:
    """
    Генератор PNG этикеток для печати через CUPS

    Преимущества перед TSPL:
    - Универсальность (любой драйвер поймёт PNG)
    - Простота (PIL рисует как на холсте)
    - Надёжность (нет проблем с битами/байтами)
    """

    # DPI для термопринтера (203 dpi = стандарт)
    DPI = 203

    def __init__(self, template_config: Dict[str, Any]):
        """
        Args:
            template_config: Конфигурация шаблона (из Template.config)
        """
        self.config = template_config
        self.use_elements = "elements" in template_config

        # Размеры этикетки в пикселях (203 dpi ≈ 8 dots/mm)
        self.width_mm = template_config.get("paper_width_mm", 58)
        self.height_mm = template_config.get("paper_height_mm", 60)

        # Конвертируем мм в пиксели (203 dpi)
        self.width_px = int(self.width_mm * self.DPI / 25.4)   # 58mm ≈ 460px
        self.height_px = int(self.height_mm * self.DPI / 25.4)  # 60mm ≈ 472px

    def render(self, dish_data: Dict[str, Any]) -> bytes:
        """
        Генерирует PNG этикетку

        Args:
            dish_data: {
                "name": str,
                "weight_g": int,
                "calories": int,
                "protein": float,
                "fat": float,
                "carbs": float,
                "ingredients": [str],
                "label_type": str,
            }

        Returns:
            PNG данные (bytes)
        """
        if self.use_elements:
            return self._render_with_elements(dish_data)
        else:
            return self._render_legacy(dish_data)

    def _render_with_elements(self, dish_data: Dict[str, Any]) -> bytes:
        """
        Рендеринг с использованием elements[] из визуального редактора

        Args:
            dish_data: Данные блюда

        Returns:
            PNG данные
        """
        # Создаём белое изображение
        img = Image.new('RGB', (self.width_px, self.height_px), 'white')
        draw = ImageDraw.Draw(img)

        # Даты
        now = datetime.now()
        shelf_life_hours = self.config.get("shelf_life_hours", 6)
        shelf_life = now + timedelta(hours=shelf_life_hours)

        # Обрабатываем элементы
        elements = self.config.get("elements", [])

        for element in elements:
            if not element.get("visible", True):
                continue

            element_type = element.get("type")
            position = element.get("position", {})

            # Конвертируем мм в пиксели
            x_px = int(position.get("x", 10) * self.DPI / 25.4)
            y_px = int(position.get("y", 10) * self.DPI / 25.4)

            font_size = element.get("fontSize", 14)
            font_weight = element.get("fontWeight", "normal")

            # Загружаем шрифт с учётом жирности
            try:
                if font_weight == "bold":
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                else:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except:
                font = ImageFont.load_default()

            # Рендерим элемент в зависимости от типа
            if element_type == "dish_name":
                # Название блюда
                text = dish_data.get("name", "")
                if text:
                    draw.text((x_px, y_px), text, font=font, fill='black')

            elif element_type == "text":
                field_name = element.get("fieldName")
                if field_name == "dish_name":
                    text = dish_data.get("name", "")
                else:
                    text = element.get("content", "")

                if text:
                    draw.text((x_px, y_px), text, font=font, fill='black')

            elif element_type == "weight":
                weight_g = dish_data.get("weight_g", 0)
                calories = dish_data.get("calories", 0)
                show_unit = element.get("showUnit", True)
                unit = "г" if show_unit else ""

                text = f"Вес: {weight_g}{unit}  Ккал: {calories}"
                draw.text((x_px, y_px), text, font=font, fill='black')

            elif element_type == "bju":
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
                draw.text((x_px, y_px), text, font=font, fill='black')

            elif element_type == "composition":
                ingredients = dish_data.get("ingredients", [])
                max_lines = element.get("maxLines", 3)

                if ingredients:
                    ingredients_text = ", ".join(ingredients[:max_lines])

                    # Ограничиваем длину
                    max_length = 50
                    if len(ingredients_text) > max_length:
                        ingredients_text = ingredients_text[:max_length-3] + "..."

                    text = f"Состав: {ingredients_text}"
                    draw.text((x_px, y_px), text, font=font, fill='black')

            elif element_type == "datetime":
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
                draw.text((x_px, y_px), text, font=font, fill='black')

            elif element_type == "shelf_life":
                label = element.get("label", "Годен до:")
                hours = element.get("hours", shelf_life_hours)
                expiry = now + timedelta(hours=hours)

                date_str = expiry.strftime("%d.%m %H:%M")
                text = f"{label} {date_str}"
                draw.text((x_px, y_px), text, font=font, fill='black')

        # Конвертируем в PNG bytes
        output = io.BytesIO()
        img.save(output, format='PNG', dpi=(self.DPI, self.DPI))
        png_bytes = output.getvalue()

        logger.debug(f"Generated PNG label for {dish_data['name']}: {len(png_bytes)} bytes")

        return png_bytes

    def _render_legacy(self, dish_data: Dict[str, Any]) -> bytes:
        """
        Старый метод рендеринга (для обратной совместимости)

        Args:
            dish_data: Данные блюда

        Returns:
            PNG данные
        """
        # Создаём белое изображение
        img = Image.new('RGB', (self.width_px, self.height_px), 'white')
        draw = ImageDraw.Draw(img)

        # Загружаем шрифты
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            font_title = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Даты
        now = datetime.now()
        shelf_life_hours = self.config.get("shelf_life_hours", 6)
        shelf_life = now + timedelta(hours=shelf_life_hours)

        y = 20  # Начальная позиция по Y

        # Название блюда
        title_text = dish_data["name"]
        if len(title_text) > 25:
            title_text = title_text[:25-3] + "..."
        draw.text((10, y), title_text, font=font_title, fill='black')
        y += 40

        # Вес и калории
        wc_text = f'Вес: {dish_data["weight_g"]}г | {dish_data["calories"]} ккал'
        draw.text((10, y), wc_text, font=font_medium, fill='black')
        y += 30

        # БЖУ
        if self.config.get("bju", {}).get("enabled", True):
            bju_text = f'Б:{dish_data["protein"]:.0f}г Ж:{dish_data["fat"]:.0f}г У:{dish_data["carbs"]:.0f}г'
            draw.text((10, y), bju_text, font=font_medium, fill='black')
            y += 30

        # Состав
        if self.config.get("ingredients", {}).get("enabled", True) and dish_data.get("ingredients"):
            ingredients_text = ", ".join(dish_data["ingredients"][:3])
            if len(ingredients_text) > 50:
                ingredients_text = ingredients_text[:50-3] + "..."

            draw.text((10, y), f"Состав: {ingredients_text}", font=font_small, fill='black')
            y += 30

        # Дата изготовления
        date_str = now.strftime("%d.%m %H:%M")
        draw.text((10, y), f"Изготовлено: {date_str}", font=font_small, fill='black')
        y += 25

        # Срок годности
        shelf_str = shelf_life.strftime("%d.%m %H:%M")
        draw.text((10, y), f"Годен до: {shelf_str}", font=font_small, fill='black')

        # Конвертируем в PNG bytes
        output = io.BytesIO()
        img.save(output, format='PNG', dpi=(self.DPI, self.DPI))
        png_bytes = output.getvalue()

        logger.debug(f"Generated PNG label (legacy) for {dish_data['name']}: {len(png_bytes)} bytes")

        return png_bytes


# ============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ============================================================================

def example_usage():
    """Пример использования ImageLabelRenderer"""

    template_config = {
        "paper_width_mm": 58,
        "paper_height_mm": 60,
        "paper_gap_mm": 2,
        "shelf_life_hours": 6,
    }

    dish_data = {
        "name": "Лепешка с говядиной",
        "weight_g": 259,
        "calories": 380,
        "protein": 25.0,
        "fat": 15.0,
        "carbs": 40.0,
        "ingredients": ["говядина", "тесто", "лук", "специи"],
        "label_type": "MAIN"
    }

    renderer = ImageLabelRenderer(template_config)
    png_bytes = renderer.render(dish_data)

    print(f"Сгенерирован PNG: {len(png_bytes)} байт")

    # Сохраняем для проверки
    with open("/tmp/label_test.png", "wb") as f:
        f.write(png_bytes)
    print("Сохранено в /tmp/label_test.png")


if __name__ == "__main__":
    example_usage()
