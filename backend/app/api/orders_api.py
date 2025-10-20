"""
Orders API - CRUD операции с заказами
Endpoint для работы с заказами из UI
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Order, OrderItem, PrintJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orders", tags=["orders"])


# ============================================================================
# SCHEMAS
# ============================================================================

class PrintJobSchema(BaseModel):
    """Схема PrintJob для ответа"""
    id: int
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    printed_at: Optional[datetime]
    retry_count: int
    error_message: Optional[str]

    class Config:
        from_attributes = True


class OrderItemSchema(BaseModel):
    """Схема OrderItem для ответа"""
    id: int
    rk_code: str
    name: str
    uni: int
    quantity: int
    price: float
    modifier_id: Optional[str]
    modifier_name: Optional[str]
    created_at: datetime
    print_jobs: List[PrintJobSchema]

    class Config:
        from_attributes = True


class OrderSchema(BaseModel):
    """Схема Order для ответа"""
    id: int
    visit_id: str
    order_ident: str
    table_code: str
    status: str
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemSchema]

    class Config:
        from_attributes = True


class OrderListItemSchema(BaseModel):
    """Схема Order для списка (без items, краткая информация)"""
    id: int
    visit_id: str
    order_ident: str
    table_code: str
    status: str
    created_at: datetime
    updated_at: datetime
    items_count: int
    jobs_count: int
    jobs_done: int
    jobs_failed: int

    class Config:
        from_attributes = True


class ReprintRequest(BaseModel):
    """Запрос на повторную печать"""
    order_item_id: int
    quantity: Optional[int] = None  # Если None - печатаем все порции


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[OrderListItemSchema])
async def get_orders(
    status: Optional[str] = Query(None, description="Фильтр по статусу: NOT_PRINTED, PRINTING, DONE, FAILED"),
    table_code: Optional[str] = Query(None, description="Фильтр по столу"),
    limit: int = Query(100, description="Максимум заказов"),
    offset: int = Query(0, description="Смещение для пагинации"),
    db: Session = Depends(get_db)
):
    """
    Получить список заказов

    Фильтры:
    - status: Статус заказа (NOT_PRINTED, PRINTING, DONE, FAILED)
    - table_code: Код стола
    - limit/offset: Пагинация

    Сортировка: по дате создания (новые сверху)
    """
    query = db.query(Order)

    # Фильтры
    if status:
        query = query.filter(Order.status == status)

    if table_code:
        query = query.filter(Order.table_code == table_code)

    # Сортировка (новые сверху)
    query = query.order_by(desc(Order.created_at))

    # Пагинация
    query = query.limit(limit).offset(offset)

    orders = query.all()

    # Формируем ответ
    result = []
    for order in orders:
        # Считаем статистику jobs
        all_jobs = []
        for item in order.items:
            all_jobs.extend(item.print_jobs)

        jobs_count = len(all_jobs)
        jobs_done = len([j for j in all_jobs if j.status == "DONE"])
        jobs_failed = len([j for j in all_jobs if j.status == "FAILED"])

        result.append(OrderListItemSchema(
            id=order.id,
            visit_id=order.visit_id,
            order_ident=order.order_ident,
            table_code=order.table_code,
            status=order.status,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items_count=len(order.items),
            jobs_count=jobs_count,
            jobs_done=jobs_done,
            jobs_failed=jobs_failed,
        ))

    return result


@router.get("/{order_id}", response_model=OrderSchema)
async def get_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    Получить детальную информацию о заказе

    Включает:
    - Все items
    - Все print jobs для каждого item
    """
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


@router.delete("/{order_id}")
async def delete_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    Удалить заказ

    ВНИМАНИЕ: Каскадно удаляет все OrderItem и PrintJob

    Использование:
    - Очистка старых заказов
    - Отмена ошибочных заказов
    """
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Удаляем (каскадно удалятся items и jobs)
    db.delete(order)
    db.commit()

    logger.info(f"🗑️  Deleted order #{order_id}")

    return {"success": True, "message": f"Order #{order_id} deleted"}


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    Отменить заказ

    Отменяет все QUEUED print jobs и меняет статус заказа на CANCELLED
    """
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Отменяем все QUEUED jobs
    cancelled_count = 0
    for item in order.items:
        for job in item.print_jobs:
            if job.status == "QUEUED":
                job.status = "CANCELLED"
                cancelled_count += 1

    # Меняем статус заказа
    order.status = "CANCELLED"
    db.commit()

    logger.info(f"❌ Cancelled order #{order_id}, jobs cancelled: {cancelled_count}")

    return {
        "success": True,
        "message": f"Order #{order_id} cancelled",
        "jobs_cancelled": cancelled_count
    }


@router.post("/reprint", response_model=dict)
async def reprint_item(
    request: ReprintRequest,
    db: Session = Depends(get_db)
):
    """
    Повторная печать item

    Создаёт новые PrintJob для указанного OrderItem

    Args:
        order_item_id: ID order item
        quantity: Количество порций (если None - все порции item)
    """
    from app.core.database import dishes_db
    from app.models import Template
    from app.services.printer.tspl_renderer import TSPLRenderer

    # Получаем OrderItem
    order_item = db.query(OrderItem).filter(OrderItem.id == request.order_item_id).first()

    if not order_item:
        raise HTTPException(status_code=404, detail="OrderItem not found")

    # Количество порций
    quantity = request.quantity if request.quantity is not None else order_item.quantity

    # Получаем данные блюда
    dish = dishes_db.get_dish_by_rk_code(order_item.rk_code)
    if not dish:
        raise HTTPException(
            status_code=404,
            detail=f"Dish {order_item.rk_code} not found in database"
        )

    # Получаем шаблон
    template = db.query(Template).filter(Template.is_default == True).first()
    if not template:
        raise HTTPException(status_code=500, detail="Default template not found")

    renderer = TSPLRenderer(template.config)

    # Создаём новые PrintJob
    jobs_created = 0

    # Основные этикетки
    for i in range(quantity):
        tspl = renderer.render({
            "name": dish["name"],
            "rk_code": dish["rkeeper_code"],
            "weight_g": dish["weight_g"],
            "calories": dish["calories"],
            "protein": dish["protein"],
            "fat": dish["fat"],
            "carbs": dish["carbs"],
            "ingredients": dish["ingredients"],
            "label_type": "MAIN",
        })

        job = PrintJob(
            order_item_id=order_item.id,
            tspl_data=tspl,
            status="QUEUED",
            retry_count=0,
            max_retries=3,
        )
        db.add(job)
        jobs_created += 1

    # Дополнительные этикетки
    if dish.get("has_extra_labels") and dish.get("extra_labels"):
        for extra in dish["extra_labels"]:
            for i in range(quantity):
                tspl = renderer.render({
                    "name": extra["extra_dish_name"],
                    "rk_code": dish["rkeeper_code"],
                    "weight_g": extra["extra_dish_weight_g"],
                    "calories": extra["extra_dish_calories"],
                    "protein": extra.get("extra_dish_protein", 0),
                    "fat": extra.get("extra_dish_fat", 0),
                    "carbs": extra.get("extra_dish_carbs", 0),
                    "ingredients": [],
                    "label_type": "EXTRA",
                })

                job = PrintJob(
                    order_item_id=order_item.id,
                    tspl_data=tspl,
                    status="QUEUED",
                    retry_count=0,
                    max_retries=3,
                )
                db.add(job)
                jobs_created += 1

    db.commit()

    logger.info(f"🔄 Reprint: order_item #{order_item.id}, jobs created: {jobs_created}")

    return {
        "success": True,
        "message": f"Created {jobs_created} print jobs for reprint",
        "jobs_created": jobs_created
    }


@router.delete("/cleanup")
async def cleanup_old_orders(
    days: int = Query(7, description="Удалить заказы старше N дней"),
    db: Session = Depends(get_db)
):
    """
    Очистка старых заказов

    Удаляет заказы старше указанного количества дней

    ВНИМАНИЕ: Необратимая операция!
    """
    cutoff_date = datetime.now() - timedelta(days=days)

    # Находим старые заказы
    old_orders = db.query(Order).filter(Order.created_at < cutoff_date).all()

    count = len(old_orders)

    # Удаляем
    for order in old_orders:
        db.delete(order)

    db.commit()

    logger.info(f"🧹 Cleanup: deleted {count} orders older than {days} days")

    return {
        "success": True,
        "message": f"Deleted {count} orders older than {days} days",
        "deleted_count": count
    }
