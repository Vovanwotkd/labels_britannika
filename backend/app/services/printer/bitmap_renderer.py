"""
Bitmap Renderer для TSPL
Рендерит текст (включая кириллицу) в bitmap для принтеров без поддержки Unicode
"""

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class BitmapRenderer:
    """
    Рендерит текст в монохромный bitmap для TSPL команды BITMAP

    Используется для печати кириллицы на принтерах без Unicode поддержки
    """

    @staticmethod
    def text_to_bitmap_tspl(text: str, x: int, y: int, font_size: int = 20, width: int = 400) -> str:
        """
        Конвертирует текст в TSPL команду BITMAP

        Args:
            text: Текст для рендеринга
            x: X координата (в dots)
            y: Y координата (в dots)
            font_size: Размер шрифта (пиксели)
            width: Максимальная ширина текста (пиксели)

        Returns:
            TSPL команда BITMAP
        """
        try:
            # Создаём изображение с запасом по высоте
            img_height = font_size + 10
            img = Image.new('1', (width, img_height), 1)  # 1 = белый фон
            draw = ImageDraw.Draw(img)

            # Используем дефолтный шрифт (поддерживает кириллицу)
            try:
                # Попытка использовать TrueType шрифт
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except:
                # Fallback на дефолтный шрифт PIL
                font = ImageFont.load_default()

            # Рисуем текст
            draw.text((0, 0), text, font=font, fill=0)  # 0 = черный текст

            # Обрезаем пустое пространство со всех сторон (включая сверху/снизу)
            bbox = img.getbbox()
            if bbox:
                # bbox = (left, top, right, bottom)
                img = img.crop(bbox)  # Crop со всех сторон для оптимизации

            # Конвертируем в TSPL bitmap формат
            tspl_bitmap = BitmapRenderer._image_to_tspl_bitmap(img, x, y)

            return tspl_bitmap

        except Exception as e:
            logger.error(f"Ошибка рендеринга текста в bitmap: {e}")
            # Fallback - возвращаем пустую команду
            return ""

    @staticmethod
    def _image_to_tspl_bitmap(img: Image.Image, x: int, y: int) -> str:
        """
        Конвертирует PIL Image в TSPL BITMAP команду

        Args:
            img: PIL Image (monochrome, mode '1')
            x: X позиция
            y: Y позиция

        Returns:
            TSPL команда BITMAP
        """
        width, height = img.size

        # Конвертируем изображение в байты
        # TSPL ожидает monochrome bitmap где каждый байт = 8 пикселей
        bytes_per_row = (width + 7) // 8  # округляем вверх

        bitmap_data = []
        for row in range(height):
            row_bytes = []
            for byte_idx in range(bytes_per_row):
                byte_value = 0
                for bit_idx in range(8):
                    pixel_x = byte_idx * 8 + bit_idx
                    if pixel_x < width:
                        # Получаем пиксель (0=черный, 1=белый в mode '1')
                        pixel = img.getpixel((pixel_x, row))
                        # TSPL: попробуем без инверсии (1=черный)
                        if pixel == 1:
                            byte_value |= (1 << (7 - bit_idx))

                row_bytes.append(f"{byte_value:02X}")

            bitmap_data.append("".join(row_bytes))

        # Формируем TSPL команду
        # BITMAP x, y, width_bytes, height, mode, data
        # mode: 0=OVERWRITE (recommended), 1=OR, 2=XOR
        tspl = f"BITMAP {x},{y},{bytes_per_row},{height},0,{''.join(bitmap_data)}\n"

        return tspl
