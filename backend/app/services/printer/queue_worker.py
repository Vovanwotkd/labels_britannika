"""
Print Queue Worker
Асинхронный worker для обработки очереди печати
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import PrintJob
from app.services.printer.tcp_client import PrinterClient
from app.services.websocket.manager import broadcast_print_job_update

logger = logging.getLogger(__name__)


class PrintQueueWorker:
    """
    Асинхронный worker для обработки очереди печати

    Особенности:
    - Работает в фоновом режиме
    - Обрабатывает задачи последовательно (FIFO)
    - Автоматические повторы при ошибках
    - Graceful shutdown
    """

    def __init__(self, printer_host: str, printer_port: int = 9100):
        """
        Args:
            printer_host: IP адрес принтера
            printer_port: Порт принтера (по умолчанию 9100)
        """
        self.printer_host = printer_host
        self.printer_port = printer_port
        self.printer_client = PrinterClient(printer_host, printer_port)

        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Запустить worker"""
        if self._running:
            logger.warning("⚠️  Print queue worker уже запущен")
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("🚀 Print queue worker запущен")

    async def stop(self):
        """Остановить worker (graceful shutdown)"""
        if not self._running:
            return

        logger.info("🛑 Остановка print queue worker...")
        self._running = False

        if self._task:
            # Ждём завершения текущей задачи (макс 10 секунд)
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("⚠️  Worker не остановился за 10 секунд, принудительная остановка")
                self._task.cancel()

        logger.info("✅ Print queue worker остановлен")

    async def _run(self):
        """
        Основной цикл worker

        Постоянно проверяет БД на наличие заданий со статусом QUEUED
        и обрабатывает их последовательно
        """
        logger.info("🔄 Print queue worker: начало работы")

        while self._running:
            try:
                # Обрабатываем одно задание
                await self._process_next_job()

                # Небольшая задержка перед следующей проверкой
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"❌ Ошибка в print queue worker: {e}", exc_info=True)
                # Продолжаем работу даже при ошибках
                await asyncio.sleep(1.0)

        logger.info("🏁 Print queue worker: цикл завершён")

    async def _process_next_job(self):
        """
        Обработать следующее задание из очереди

        1. Берём первое задание со статусом QUEUED
        2. Меняем статус на PRINTING
        3. Отправляем на принтер
        4. Меняем статус на DONE или FAILED
        5. При ошибке - retry (если не превышен лимит)
        """
        db = SessionLocal()

        try:
            # Получаем первое задание QUEUED (FIFO)
            job = db.query(PrintJob)\
                .filter(PrintJob.status == "QUEUED")\
                .order_by(PrintJob.created_at)\
                .first()

            if not job:
                # Нет заданий в очереди
                return

            logger.info(f"📄 Обработка job #{job.id} (order_item_id={job.order_item_id})")

            # Меняем статус на PRINTING
            job.status = "PRINTING"
            job.started_at = datetime.now()
            db.commit()

            # WebSocket broadcast - job status changed to PRINTING
            await broadcast_print_job_update(
                job_id=job.id,
                status="PRINTING",
                order_item_id=job.order_item_id
            )

            # Отправляем на принтер
            try:
                # Используем asyncio.to_thread для блокирующей операции
                success = await asyncio.to_thread(
                    self.printer_client.send,
                    job.tspl_data
                )

                if success:
                    # Успешно напечатано
                    job.status = "DONE"
                    job.printed_at = datetime.now()
                    db.commit()

                    logger.info(f"✅ Job #{job.id} напечатан успешно")

                    # WebSocket broadcast - job completed
                    await broadcast_print_job_update(
                        job_id=job.id,
                        status="DONE",
                        order_item_id=job.order_item_id
                    )

                else:
                    # Ошибка печати
                    await self._handle_job_failure(db, job, "Printer returned failure")

            except Exception as e:
                # Ошибка отправки
                await self._handle_job_failure(db, job, str(e))

        finally:
            db.close()

    async def _handle_job_failure(self, db: Session, job: PrintJob, error_message: str):
        """
        Обработать ошибку печати

        Args:
            db: Сессия БД
            job: Задание
            error_message: Сообщение об ошибке
        """
        job.retry_count += 1
        job.error_message = error_message

        if job.retry_count < job.max_retries:
            # Можем повторить
            job.status = "QUEUED"
            db.commit()

            logger.warning(
                f"⚠️  Job #{job.id} failed: {error_message}. "
                f"Retry {job.retry_count}/{job.max_retries}"
            )

            # WebSocket broadcast - job retry
            await broadcast_print_job_update(
                job_id=job.id,
                status="QUEUED",
                order_item_id=job.order_item_id
            )

            # Задержка перед повтором (экспоненциальная)
            retry_delay = min(2 ** job.retry_count, 30)  # макс 30 секунд
            await asyncio.sleep(retry_delay)

        else:
            # Превышен лимит повторов
            job.status = "FAILED"
            job.finished_at = datetime.now()
            db.commit()

            logger.error(
                f"❌ Job #{job.id} FAILED после {job.retry_count} попыток: {error_message}"
            )

            # WebSocket broadcast - job failed permanently
            await broadcast_print_job_update(
                job_id=job.id,
                status="FAILED",
                order_item_id=job.order_item_id
            )

    def is_running(self) -> bool:
        """Проверить работает ли worker"""
        return self._running


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Global instance (создаётся при старте приложения)
_worker_instance: Optional[PrintQueueWorker] = None


def get_worker() -> Optional[PrintQueueWorker]:
    """Получить global instance worker"""
    return _worker_instance


def set_worker(worker: PrintQueueWorker):
    """Установить global instance worker"""
    global _worker_instance
    _worker_instance = worker
