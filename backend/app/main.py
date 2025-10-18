"""
Britannica Labels - FastAPI приложение
Главный файл, точка входа
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import init_db
from app.services.printer.queue_worker import PrintQueueWorker, set_worker

# ============================================================================
# ЛОГИРОВАНИЕ
# ============================================================================

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# ============================================================================
# LIFESPAN (startup/shutdown события)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager для FastAPI
    Выполняется при запуске и остановке приложения
    """
    # STARTUP
    logger.info(f"🚀 Запуск {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🕐 Timezone: {settings.TIMEZONE}")

    # Инициализация БД
    logger.info("📊 Инициализация базы данных...")
    init_db()

    # Запуск print queue worker
    logger.info("🖨️  Запуск print queue worker...")
    worker = PrintQueueWorker(
        printer_host=settings.PRINTER_IP,
        printer_port=settings.PRINTER_PORT
    )
    set_worker(worker)
    await worker.start()

    # TODO: Запуск background tasks (синхронизация, архивация)

    logger.info("✅ Приложение запущено")

    yield

    # SHUTDOWN
    logger.info("🛑 Остановка приложения...")

    # Graceful shutdown print queue
    worker = worker  # worker из scope выше
    if worker:
        await worker.stop()

    logger.info("✅ Приложение остановлено")


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Система печати этикеток для ресторанов Britannica Project",
    lifespan=lifespan,
    debug=settings.DEBUG,
)


# ============================================================================
# CORS (для разработки frontend)
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # React dev server (альтернатива)
        "http://labels.local",    # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/")
async def root():
    """Главная страница API"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health")
async def health_check():
    """Health check для мониторинга"""
    return {
        "status": "healthy",
        "database": "connected",  # TODO: реальная проверка БД
        "printer": "unknown",     # TODO: проверка принтера
    }


# ============================================================================
# API ROUTERS
# ============================================================================

from app.api import print_api, webhook_api, orders_api, websocket_api, auth_api, settings_api

app.include_router(print_api.router)
app.include_router(webhook_api.router)
app.include_router(orders_api.router)
app.include_router(websocket_api.router)
app.include_router(auth_api.router)
app.include_router(settings_api.router)

# TODO: Добавить остальные роутеры
# from app.api import templates, users
# app.include_router(templates.router)
# app.include_router(users.router)


# ============================================================================
# ЗАПУСК (для dev режима)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
