"""
Test Connection API
Проверка связи с внешними системами
"""

import logging
import socket
import aiohttp
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Setting
from app.api.auth_api import require_auth
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test", tags=["test"])


# ============================================================================
# SCHEMAS
# ============================================================================

class TestResponse(BaseModel):
    """Ответ на тест подключения"""
    success: bool
    message: str
    details: Dict[str, Any] = {}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_setting_value(db: Session, key: str, default: str = "") -> str:
    """Получить значение настройки из БД"""
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting and setting.value else default


async def test_http_connection(url: str, username: str = None, password: str = None, timeout: int = 5) -> TestResponse:
    """Тест HTTP подключения"""
    try:
        auth = aiohttp.BasicAuth(username, password) if username and password else None

        # Отключаем проверку SSL сертификатов для самоподписанных сертификатов
        connector = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(auth=auth, timeout=aiohttp.ClientTimeout(total=timeout), connector=connector) as session:
            async with session.get(url) as response:
                return TestResponse(
                    success=True,
                    message=f"Успешное подключение (HTTP {response.status})",
                    details={
                        "status_code": response.status,
                        "url": url,
                        "response_time_ms": int(response.headers.get('X-Response-Time', 0))
                    }
                )
    except aiohttp.ClientError as e:
        return TestResponse(
            success=False,
            message=f"Ошибка подключения: {str(e)}",
            details={"error": str(e), "url": url}
        )
    except Exception as e:
        return TestResponse(
            success=False,
            message=f"Неизвестная ошибка: {str(e)}",
            details={"error": str(e), "url": url}
        )


def test_tcp_connection(host: str, port: int, timeout: int = 5) -> TestResponse:
    """Тест TCP подключения"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            return TestResponse(
                success=True,
                message=f"Принтер доступен на {host}:{port}",
                details={"host": host, "port": port}
            )
        else:
            return TestResponse(
                success=False,
                message=f"Не удалось подключиться к {host}:{port}",
                details={"host": host, "port": port, "error_code": result}
            )
    except socket.gaierror:
        return TestResponse(
            success=False,
            message=f"Не удалось разрешить hostname: {host}",
            details={"host": host, "error": "DNS resolution failed"}
        )
    except Exception as e:
        return TestResponse(
            success=False,
            message=f"Ошибка: {str(e)}",
            details={"host": host, "port": port, "error": str(e)}
        )


# ============================================================================
# TEST ENDPOINTS
# ============================================================================

@router.post("/printer", response_model=TestResponse)
async def test_printer_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Проверить подключение к принтеру

    Требует аутентификации
    """
    printer_ip = get_setting_value(db, "printer_ip", "192.168.1.10")
    printer_port = int(get_setting_value(db, "printer_port", "9100"))

    logger.info(f"🖨️  Testing printer connection: {printer_ip}:{printer_port}")

    result = test_tcp_connection(printer_ip, printer_port, timeout=3)

    if result.success:
        logger.info(f"✅ Printer connection successful")
    else:
        logger.warning(f"❌ Printer connection failed: {result.message}")

    return result


@router.post("/storehouse", response_model=TestResponse)
async def test_storehouse_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Проверить подключение к StoreHouse 5

    Требует аутентификации
    """
    sh5_url = get_setting_value(db, "sh5_url", "")
    sh5_user = get_setting_value(db, "sh5_user", "")
    sh5_pass = get_setting_value(db, "sh5_pass", "")

    if not sh5_url:
        return TestResponse(
            success=False,
            message="URL StoreHouse 5 не настроен",
            details={}
        )

    logger.info(f"🏪 Testing StoreHouse 5 connection: {sh5_url}")

    result = await test_http_connection(sh5_url, sh5_user, sh5_pass, timeout=5)

    if result.success:
        logger.info(f"✅ StoreHouse 5 connection successful")
    else:
        logger.warning(f"❌ StoreHouse 5 connection failed: {result.message}")

    return result


@router.post("/rkeeper", response_model=TestResponse)
async def test_rkeeper_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Проверить подключение к RKeeper

    Требует аутентификации
    """
    rk_url = get_setting_value(db, "rkeeper_url", "")
    rk_user = get_setting_value(db, "rkeeper_user", "")
    rk_pass = get_setting_value(db, "rkeeper_pass", "")

    if not rk_url:
        return TestResponse(
            success=False,
            message="URL RKeeper не настроен",
            details={}
        )

    logger.info(f"🍽️  Testing RKeeper connection: {rk_url}")

    result = await test_http_connection(rk_url, rk_user, rk_pass, timeout=5)

    if result.success:
        logger.info(f"✅ RKeeper connection successful")
    else:
        logger.warning(f"❌ RKeeper connection failed: {result.message}")

    return result
