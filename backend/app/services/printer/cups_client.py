"""
CUPS Printer Client - печать через CUPS драйвер
"""

import subprocess
import logging
import tempfile
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class CUPSPrinterClient:
    """
    Клиент для печати через CUPS (Common Unix Printing System)

    Использует официальный драйвер принтера вместо raw TSPL команд.
    Преимущества:
    - Универсальность (драйвер знает правильный формат)
    - Надёжность (официальный драйвер от производителя)
    - Гибкость (можно печатать PNG, PDF, текст)
    """

    def __init__(self, printer_name: str, cups_server: str = "localhost"):
        """
        Args:
            printer_name: Имя принтера в CUPS (например "XPrinter")
            cups_server: CUPS сервер (default "localhost" для хоста)
        """
        self.printer_name = printer_name
        self.cups_server = cups_server

    def print_file(self, file_path: str, copies: int = 1) -> bool:
        """
        Печать файла через CUPS

        Args:
            file_path: Путь к файлу (PNG, PDF, текст)
            copies: Количество копий

        Returns:
            True если успешно, False при ошибке
        """
        try:
            # Проверяем что файл существует
            if not os.path.exists(file_path):
                logger.error(f"❌ Файл не найден: {file_path}")
                return False

            # Формируем команду lp
            cmd = [
                'lp',
                '-h', self.cups_server,  # CUPS сервер
                '-d', self.printer_name,  # Имя принтера
                '-n', str(copies),        # Количество копий
                '-o', 'media=Custom.58x60mm',  # Размер этикетки
                file_path
            ]

            logger.info(f"📄 Отправка на печать: {file_path} → {self.printer_name} (x{copies})")

            # Выполняем команду
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info(f"✅ Файл отправлен на печать: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"❌ Ошибка печати: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"❌ Timeout при печати через CUPS")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка печати: {e}")
            return False

    def print_image_data(self, image_bytes: bytes, filename: str = "label.png", copies: int = 1) -> bool:
        """
        Печать изображения из байтов

        Args:
            image_bytes: Данные изображения (PNG)
            filename: Имя временного файла
            copies: Количество копий

        Returns:
            True если успешно
        """
        try:
            # Создаём временный файл
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.png', delete=False) as tmp_file:
                tmp_file.write(image_bytes)
                tmp_path = tmp_file.name

            # Печатаем файл
            success = self.print_file(tmp_path, copies)

            # Удаляем временный файл
            try:
                os.unlink(tmp_path)
            except:
                pass

            return success

        except Exception as e:
            logger.error(f"❌ Ошибка печати изображения: {e}")
            return False

    def get_printer_status(self) -> dict:
        """
        Получить статус принтера

        Returns:
            {
                "online": bool,
                "printer_name": str,
                "status": str,
                "error": Optional[str]
            }
        """
        try:
            # Выполняем lpstat -p <printer_name>
            result = subprocess.run(
                ['lpstat', '-h', self.cups_server, '-p', self.printer_name],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Парсим вывод
                status_text = result.stdout.strip()
                is_online = "idle" in status_text.lower() or "printing" in status_text.lower()

                return {
                    "online": is_online,
                    "printer_name": self.printer_name,
                    "status": status_text,
                    "error": None
                }
            else:
                return {
                    "online": False,
                    "printer_name": self.printer_name,
                    "status": "unavailable",
                    "error": result.stderr.strip()
                }

        except subprocess.TimeoutExpired:
            return {
                "online": False,
                "printer_name": self.printer_name,
                "status": "timeout",
                "error": "Timeout при проверке статуса"
            }
        except Exception as e:
            return {
                "online": False,
                "printer_name": self.printer_name,
                "status": "error",
                "error": str(e)
            }

    @staticmethod
    def list_printers(cups_server: str = "localhost") -> list:
        """
        Получить список доступных CUPS принтеров

        Args:
            cups_server: CUPS сервер

        Returns:
            Список имён принтеров
        """
        try:
            result = subprocess.run(
                ['lpstat', '-h', cups_server, '-p'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Парсим вывод lpstat -p
                # Формат: "printer XPrinter is idle. enabled since ..."
                printers = []
                for line in result.stdout.split('\n'):
                    if line.startswith('printer '):
                        parts = line.split()
                        if len(parts) >= 2:
                            printers.append(parts[1])

                logger.info(f"📋 Найдено CUPS принтеров: {len(printers)}")
                return printers
            else:
                logger.warning(f"⚠️  lpstat вернул ошибку: {result.stderr}")
                return []

        except Exception as e:
            logger.error(f"❌ Ошибка получения списка принтеров: {e}")
            return []


# ============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ============================================================================

def example_usage():
    """Пример использования CUPSPrinterClient"""

    # Создаём клиент
    printer = CUPSPrinterClient(
        printer_name="XPrinter",
        cups_server="localhost"  # или "host.docker.internal" из контейнера
    )

    # Проверяем статус
    status = printer.get_printer_status()
    print(f"Статус принтера: {status}")

    # Печатаем файл
    if status["online"]:
        success = printer.print_file("/path/to/label.png", copies=1)
        if success:
            print("✅ Печать успешна")
        else:
            print("❌ Ошибка печати")

    # Получаем список всех принтеров
    all_printers = CUPSPrinterClient.list_printers()
    print(f"Доступные принтеры: {all_printers}")


if __name__ == "__main__":
    example_usage()
