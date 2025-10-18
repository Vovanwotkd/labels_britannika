"""
Безопасность: хеширование паролей, сессии
"""

from passlib.context import CryptContext
from datetime import datetime, timedelta
import secrets
from typing import Optional

from app.core.config import settings

# ============================================================================
# PASSWORD HASHING
# ============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Хеширование пароля

    Args:
        password: Пароль в открытом виде

    Returns:
        Хеш пароля (bcrypt)
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка пароля

    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Хеш пароля из БД

    Returns:
        True если пароль верный
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

def generate_session_id() -> str:
    """
    Генерация уникального ID сессии

    Returns:
        32-символьный hex токен
    """
    return secrets.token_hex(16)


def get_session_expiry() -> datetime:
    """
    Получить дату истечения сессии

    Returns:
        datetime (сейчас + SESSION_LIFETIME_HOURS)
    """
    return datetime.utcnow() + timedelta(hours=settings.SESSION_LIFETIME_HOURS)


def is_session_expired(expires_at: datetime) -> bool:
    """
    Проверить истекла ли сессия

    Args:
        expires_at: Дата истечения сессии

    Returns:
        True если сессия истекла
    """
    return datetime.utcnow() > expires_at
