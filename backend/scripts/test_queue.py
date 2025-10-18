#!/usr/bin/env python3
"""
Тест Print Queue Worker

Проверяет работу очереди печати:
1. Создаёт несколько заданий в БД
2. Наблюдает как worker их обрабатывает
3. Выводит статистику
"""

import sys
import time
from pathlib import Path

# Добавляем путь к app в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models import PrintJob
from app.services.printer.tspl_renderer import TSPLRenderer

# Простой шаблон для теста
SIMPLE_TEMPLATE = {
    "paper_width_mm": 60,
    "paper_height_mm": 60,
    "paper_gap_mm": 2,
    "shelf_life_hours": 6,
    "title": {"font": "3", "x": 10, "y": 30, "max_width": 200},
    "weight_calories": {"font": "2", "x": 10, "y": 60},
    "bju": {"enabled": True, "font": "2", "x": 10, "y": 80},
    "ingredients": {"enabled": False, "font": "1", "x": 10, "y": 100, "max_lines": 3},
    "datetime_shelf": {"font": "2", "x": 10, "y": 140},
    "barcode": {"type": "128", "x": 10, "y": 170, "height": 50, "narrow_bar": 2},
}


def create_test_jobs(count: int = 5):
    """
    Создать тестовые задания печати

    Args:
        count: Количество заданий
    """
    print(f"\n{'='*70}")
    print(f"Создание {count} тестовых заданий...")
    print(f"{'='*70}\n")

    db = SessionLocal()
    renderer = TSPLRenderer(SIMPLE_TEMPLATE)

    created_jobs = []

    for i in range(count):
        # Генерируем TSPL для тестового блюда
        tspl = renderer.render({
            "name": f"Тестовое блюдо #{i+1}",
            "rk_code": f"TEST{i+1:03d}",
            "weight_g": 150,
            "calories": 250,
            "protein": 10,
            "fat": 15,
            "carbs": 20,
            "ingredients": ["Тестовый ингредиент 1", "Тестовый ингредиент 2"],
            "label_type": "MAIN"
        })

        # Создаём PrintJob
        job = PrintJob(
            order_item_id=None,
            tspl_data=tspl,
            status="QUEUED",
            retry_count=0,
            max_retries=3
        )
        db.add(job)
        created_jobs.append(job)

    db.commit()

    print(f"✅ Создано {len(created_jobs)} заданий:")
    for job in created_jobs:
        print(f"   - Job #{job.id} (статус: {job.status})")

    db.close()

    return [job.id for job in created_jobs]


def monitor_jobs(job_ids: list, timeout: int = 60):
    """
    Мониторинг выполнения заданий

    Args:
        job_ids: ID заданий для отслеживания
        timeout: Таймаут в секундах
    """
    print(f"\n{'='*70}")
    print(f"Мониторинг выполнения заданий (таймаут: {timeout}s)...")
    print(f"{'='*70}\n")

    db = SessionLocal()
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time

        if elapsed > timeout:
            print("\n⏱️  Превышен таймаут!")
            break

        # Проверяем статус всех заданий
        jobs = db.query(PrintJob).filter(PrintJob.id.in_(job_ids)).all()

        # Группируем по статусам
        status_counts = {}
        for job in jobs:
            status_counts[job.status] = status_counts.get(job.status, 0) + 1

        # Выводим статистику
        print(f"\r[{elapsed:05.1f}s] ", end="")
        print(f"QUEUED: {status_counts.get('QUEUED', 0):2d} | ", end="")
        print(f"PRINTING: {status_counts.get('PRINTING', 0):2d} | ", end="")
        print(f"DONE: {status_counts.get('DONE', 0):2d} | ", end="")
        print(f"FAILED: {status_counts.get('FAILED', 0):2d}", end="", flush=True)

        # Проверяем завершились ли все задания
        if all(job.status in ("DONE", "FAILED") for job in jobs):
            print("\n\n✅ Все задания обработаны!")
            break

        time.sleep(0.5)

    db.close()

    # Финальная статистика
    print(f"\n{'='*70}")
    print("ФИНАЛЬНАЯ СТАТИСТИКА:")
    print(f"{'='*70}\n")

    db = SessionLocal()
    jobs = db.query(PrintJob).filter(PrintJob.id.in_(job_ids)).all()

    for job in jobs:
        status_icon = "✅" if job.status == "DONE" else "❌" if job.status == "FAILED" else "⏳"
        print(f"{status_icon} Job #{job.id:3d} - {job.status:8s}", end="")

        if job.retry_count > 0:
            print(f" (retry: {job.retry_count})", end="")

        if job.error_message:
            print(f" - {job.error_message}", end="")

        print()

    db.close()


def main():
    """Главная функция"""
    print(f"\n{'='*70}")
    print("BRITANNICA LABELS - Тест Print Queue Worker")
    print(f"{'='*70}")

    # Создаём тестовые задания
    job_ids = create_test_jobs(count=5)

    print("\n⚠️  ВАЖНО: Убедитесь что сервер запущен!")
    print("   cd backend")
    print("   python app/main.py")
    print()

    input("Нажмите Enter когда сервер будет готов...")

    # Мониторим выполнение
    monitor_jobs(job_ids, timeout=60)

    print(f"\n{'='*70}")
    print("Тест завершён!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
