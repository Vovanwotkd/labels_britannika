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

    def _get_printer_client(self, db: Session) -> PrinterClient:
        """
        Получить PrinterClient с актуальными настройками из БД

        Args:
            db: Сессия БД

        Returns:
            PrinterClient с настройками из БД или из config (fallback)
        """
        from app.models import Setting
        from app.core.config import settings

        # Пытаемся получить настройки из БД
        printer_ip_setting = db.query(Setting).filter(Setting.key == "printer_ip").first()
        printer_port_setting = db.query(Setting).filter(Setting.key == "printer_port").first()

        # Используем настройки из БД или fallback на config
        printer_ip = printer_ip_setting.value if printer_ip_setting and printer_ip_setting.value else self.printer_host
        printer_port = int(printer_port_setting.value) if printer_port_setting and printer_port_setting.value else self.printer_port

        # Если настройки изменились, логируем
        if printer_ip != self.printer_host or printer_port != self.printer_port:
            logger.info(f"📝 Используем настройки принтера из БД: {printer_ip}:{printer_port}")

        return PrinterClient(printer_ip, printer_port)

    async def _print_via_tcp(self, db: Session, job: PrintJob) -> bool:
        """
        Печать через TCP с использованием raw TSPL

        Args:
            db: Сессия БД
            job: Задание на печать

        Returns:
            True если успешно, False при ошибке
        """
        try:
            # Получаем PrinterClient с актуальными настройками
            printer_client = self._get_printer_client(db)

            # job.tspl_data уже содержит готовый TSPL код
            success = printer_client.send_tspl(job.tspl_data)

            return success

        except Exception as e:
            logger.error(f"Ошибка печати через TCP: {e}", exc_info=True)
            return False

    async def _print_via_cups(self, db: Session, job: PrintJob) -> bool:
        """
        Печать через CUPS драйвер с использованием PNG рендеринга

        Args:
            db: Сессия БД
            job: Задание на печать

        Returns:
            True если успешно, False при ошибке
        """
        try:
            from app.models import Setting, OrderItem, Template
            from app.services.printer.cups_client import CUPSPrinterClient
            from app.services.printer.image_label_renderer import ImageLabelRenderer
            from app.core.database import dishes_db

            # 1. Получаем имя CUPS принтера из настроек
            printer_name_setting = db.query(Setting).filter(Setting.key == "printer_name").first()
            if not printer_name_setting or not printer_name_setting.value:
                raise ValueError("CUPS printer name not configured in settings")

            printer_name = printer_name_setting.value
            logger.info(f"📝 Используем CUPS принтер: {printer_name}")

            # 2. Получаем OrderItem для доступа к данным заказа
            order_item = db.query(OrderItem).filter(OrderItem.id == job.order_item_id).first()
            if not order_item:
                raise ValueError(f"OrderItem {job.order_item_id} not found")

            # 3. Получаем данные блюда из dishes_db
            dish = dishes_db.get_dish_by_rk_code(order_item.rkeeper_code)
            if not dish:
                raise ValueError(f"Dish with rk_code={order_item.rkeeper_code} not found in dishes DB")

            # 4. Получаем шаблон
            template = db.query(Template).filter(Template.is_default == True).first()
            if not template:
                raise ValueError("No default template found")

            # 5. Подготавливаем данные для рендеринга
            dish_data = {
                "name": dish["name"],
                "rk_code": dish["rkeeper_code"],
                "weight_g": dish["weight_g"],
                "calories": dish["calories"],
                "protein": dish["protein"],
                "fat": dish["fat"],
                "carbs": dish["carbs"],
                "ingredients": dish.get("ingredients", []),
                "label_type": order_item.label_type or "MAIN",
                # Дополнительные данные из order_item
                "best_before_hours": order_item.best_before_hours,
                "production_datetime": order_item.production_datetime,
            }

            # 6. Генерируем PNG
            logger.info(f"🎨 Генерируем PNG для блюда: {dish_data['name']}")
            renderer = ImageLabelRenderer(template.config)
            png_bytes = renderer.render(dish_data)

            logger.info(f"✅ PNG сгенерирован: {len(png_bytes)} bytes ({len(png_bytes)/1024:.2f} KB)")

            # 7. Отправляем на печать через CUPS
            cups_client = CUPSPrinterClient(printer_name, cups_server="host.docker.internal")
            success = cups_client.print_image_data(
                png_bytes,
                filename=f"label_{job.id}.png",
                copies=1
            )

            return success

        except Exception as e:
            logger.error(f"Ошибка печати через CUPS: {e}", exc_info=True)
            return False

    async def _process_next_job(self):
        """
        Обработать следующее задание из очереди

        1. Берём первое задание со статусом QUEUED
        2. Меняем статус на PRINTING
        3. Отправляем на принтер (CUPS или TCP в зависимости от настроек)
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
                # Проверяем тип подключения к принтеру
                from app.models import Setting
                printer_type_setting = db.query(Setting).filter(Setting.key == "printer_type").first()
                printer_type = printer_type_setting.value if printer_type_setting else "tcp"

                success = False

                if printer_type == "cups":
                    # Печать через CUPS драйвер
                    success = await self._print_via_cups(db, job)
                else:
                    # Печать через TCP (raw TSPL)
                    success = await self._print_via_tcp(db, job)

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
