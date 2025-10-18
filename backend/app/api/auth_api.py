"""
Authentication API
Аутентификация пользователей (логин, логаут)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import verify_password, generate_session_id
from app.models import User, Session as UserSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Срок действия сессии (7 дней)
SESSION_LIFETIME_DAYS = 7


# ============================================================================
# SCHEMAS
# ============================================================================

class LoginRequest(BaseModel):
    """Запрос на вход"""
    login: str
    password: str


class LoginResponse(BaseModel):
    """Ответ на вход"""
    success: bool
    message: str
    user: Optional[dict] = None


class CurrentUserResponse(BaseModel):
    """Текущий пользователь"""
    id: int
    login: str
    role: str
    full_name: Optional[str]


# ============================================================================
# DEPENDENCIES
# ============================================================================

def get_current_user(
    session_id: Optional[str] = Cookie(None, alias="session_id"),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Получить текущего пользователя по session_id из cookie

    Args:
        session_id: Session ID из cookie
        db: Database session

    Returns:
        User объект или None
    """
    if not session_id:
        return None

    # Ищем активную сессию
    session = db.query(UserSession).filter(
        UserSession.session_id == session_id,
        UserSession.expires_at > datetime.now()
    ).first()

    if not session:
        return None

    # Возвращаем пользователя
    user = db.query(User).filter(User.id == session.user_id).first()

    return user


def require_auth(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency для эндпоинтов, требующих аутентификации

    Raises:
        HTTPException: Если пользователь не авторизован
    """
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    return current_user


def require_admin(
    current_user: User = Depends(require_auth)
) -> User:
    """
    Dependency для эндпоинтов, требующих прав администратора

    Raises:
        HTTPException: Если пользователь не администратор
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Вход в систему

    Args:
        login: Логин пользователя
        password: Пароль

    Returns:
        LoginResponse с данными пользователя

    Set-Cookie: session_id
    """
    # Ищем пользователя
    user = db.query(User).filter(User.login == request.login).first()

    if not user:
        logger.warning(f"🔒 Login failed: user '{request.login}' not found")
        raise HTTPException(
            status_code=401,
            detail="Invalid login or password"
        )

    # Проверяем пароль
    if not verify_password(request.password, user.password_hash):
        logger.warning(f"🔒 Login failed: invalid password for user '{request.login}'")
        raise HTTPException(
            status_code=401,
            detail="Invalid login or password"
        )

    # Создаём сессию
    session_id = generate_session_id()
    expires_at = datetime.now() + timedelta(days=SESSION_LIFETIME_DAYS)

    session = UserSession(
        user_id=user.id,
        session_id=session_id,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()

    # Устанавливаем cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=SESSION_LIFETIME_DAYS * 24 * 60 * 60,  # в секундах
        httponly=True,
        samesite="lax",
    )

    logger.info(f"✅ Login successful: user '{user.login}' (role={user.role})")

    return LoginResponse(
        success=True,
        message="Login successful",
        user={
            "id": user.id,
            "login": user.login,
            "role": user.role,
            "full_name": user.full_name,
        }
    )


@router.post("/logout")
async def logout(
    response: Response,
    session_id: Optional[str] = Cookie(None, alias="session_id"),
    db: Session = Depends(get_db)
):
    """
    Выход из системы

    Удаляет сессию из БД и очищает cookie
    """
    if session_id:
        # Удаляем сессию из БД
        session = db.query(UserSession).filter(
            UserSession.session_id == session_id
        ).first()

        if session:
            db.delete(session)
            db.commit()
            logger.info(f"✅ Logout successful: session {session_id}")

    # Очищаем cookie
    response.delete_cookie(key="session_id")

    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_info(
    current_user: User = Depends(require_auth)
):
    """
    Получить информацию о текущем пользователе

    Требует аутентификации
    """
    return CurrentUserResponse(
        id=current_user.id,
        login=current_user.login,
        role=current_user.role,
        full_name=current_user.full_name,
    )


@router.get("/check")
async def check_auth(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Проверить авторизован ли пользователь

    Не требует аутентификации, возвращает текущий статус
    """
    if current_user:
        return {
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "login": current_user.login,
                "role": current_user.role,
                "full_name": current_user.full_name,
            }
        }
    else:
        return {
            "authenticated": False,
            "user": None
        }


@router.delete("/sessions/cleanup")
async def cleanup_expired_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Очистка истёкших сессий

    Требует прав администратора
    """
    # Удаляем истёкшие сессии
    deleted = db.query(UserSession).filter(
        UserSession.expires_at < datetime.now()
    ).delete()

    db.commit()

    logger.info(f"🧹 Cleaned up {deleted} expired sessions")

    return {
        "success": True,
        "message": f"Deleted {deleted} expired sessions",
        "deleted_count": deleted
    }
