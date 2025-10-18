"""
TCP:9100 Client - отправка TSPL команд на принтер
"""

import socket
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PrinterClient:
    """
    Клиент для отправки TSPL команд на термопринтер через TCP:9100

    Принтер: PC-365B / XP-D365B
    Протокол: TCP Raw (порт 9100)
    """

    def __init__(self, host: str, port: int = 9100, timeout: int = 5):
        """
        Args:
            host: IP адрес принтера
            port: Порт (обычно 9100)
            timeout: Таймаут подключения (секунды)
        """
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, tspl_data: str) -> bool:
        """
        Отправляет TSPL команды на принтер

        Args:
            tspl_data: TSPL команды (строка)

        Returns:
            True если успешно, False при ошибке
        """
        try:
            # Создаём TCP socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)

                # Подключаемся к принтеру
                logger.info(f"Подключение к принтеру {self.host}:{self.port}...")
                sock.connect((self.host, self.port))

                # Отправляем TSPL данные
                tspl_bytes = tspl_data.encode('utf-8')
                sock.sendall(tspl_bytes)

                logger.info(f"✅ Отправлено {len(tspl_bytes)} байт на принтер {self.host}:{self.port}")
                return True

        except socket.timeout:
            logger.error(f"❌ Timeout при подключении к принтеру {self.host}:{self.port}")
            return False

        except ConnectionRefusedError:
            logger.error(f"❌ Принтер {self.host}:{self.port} отклонил подключение (Connection refused)")
            return False

        except OSError as e:
            logger.error(f"❌ Ошибка сети при подключении к принтеру {self.host}:{self.port}: {e}")
            return False

        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при отправке на принтер: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Проверяет доступность принтера (без печати)

        Returns:
            True если принтер доступен
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
                logger.info(f"✅ Принтер {self.host}:{self.port} доступен")
                return True

        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            logger.warning(f"⚠️  Принтер {self.host}:{self.port} недоступен: {e}")
            return False

    def get_status(self) -> dict:
        """
        Получает статус принтера

        Returns:
            {
                "online": bool,
                "host": str,
                "port": int,
                "error": Optional[str]
            }
        """
        online = self.test_connection()

        return {
            "online": online,
            "host": self.host,
            "port": self.port,
            "error": None if online else "Принтер недоступен"
        }


# ============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ============================================================================

def example_usage():
    """Пример использования PrinterClient"""

    # Создаём клиент
    printer = PrinterClient(
        host="192.168.1.10",  # IP принтера
        port=9100,
        timeout=5
    )

    # Проверяем доступность
    if printer.test_connection():
        print("✅ Принтер онлайн")
    else:
        print("❌ Принтер офлайн")
        return

    # Тестовая TSPL команда (простая этикетка)
    test_tspl = """SIZE 60 mm, 40 mm
GAP 2 mm, 0 mm
DIRECTION 1
CLS
TEXT 10,10,"3",0,1,1,"ТЕСТ ПРИНТЕРА"
TEXT 10,50,"2",0,1,1,"PC-365B"
BARCODE 10,90,"128",50,1,0,2,2,"TEST123"
PRINT 1
"""

    # Отправляем на печать
    success = printer.send(test_tspl)

    if success:
        print("✅ Тестовая этикетка отправлена на печать")
    else:
        print("❌ Ошибка печати")


if __name__ == "__main__":
    example_usage()
