"""
Модели для заказов и очереди печати
"""

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base


class Order(Base):
    """
    Заказ из RKeeper
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(String, nullable=False, index=True)  # RKeeper visit ID
    order_ident = Column(String, nullable=False, index=True)  # RKeeper order ID
    table_code = Column(String, nullable=False, index=True)  # Код стола (141)
    order_total = Column(Numeric(10, 2), nullable=True)  # Сумма заказа
    status = Column(String, nullable=False, default="NOT_PRINTED", index=True)
    # Статусы: NOT_PRINTED, QUEUED, PRINTING, DONE, FAILED, CANCELLED

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)  # Когда заказ закрыт в RKeeper

    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    print_jobs = relationship("PrintJob", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order {self.order_ident} (стол {self.table_code}) - {self.status}>"


class OrderItem(Base):
    """
    Позиция заказа (блюдо)
    """
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    rk_code = Column(String, nullable=False, index=True)  # RKeeper код блюда
    quantity = Column(Integer, nullable=False, default=1)  # Количество порций
    dish_name = Column(String, nullable=True)  # Кеш названия из dishes_with_extras
    weight_g = Column(Integer, nullable=True)  # Вес одной порции (грамм)

    printed_count = Column(Integer, default=0)  # Сколько раз напечатали
    last_printed_at = Column(DateTime(timezone=True), nullable=True)  # Последняя печать

    # Relationships
    order = relationship("Order", back_populates="items")
    print_jobs = relationship("PrintJob", back_populates="order_item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OrderItem {self.dish_name} x{self.quantity}>"


class PrintJob(Base):
    """
    Задание на печать (в очереди)
    """
    __tablename__ = "print_jobs"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=True, index=True)
    # order_item_id = NULL → печать всего заказа, NOT NULL → печать конкретного блюда

    label_type = Column(String, nullable=False)  # MAIN, EXTRA
    dish_rid = Column(Integer, nullable=True)  # RID блюда из dishes_with_extras
    tspl_data = Column(Text, nullable=False)  # TSPL команды для принтера

    status = Column(String, nullable=False, default="QUEUED", index=True)
    # Статусы: QUEUED, PRINTING, DONE, FAILED

    retry_count = Column(Integer, default=0)  # Количество попыток
    max_retries = Column(Integer, default=3)  # Максимум попыток
    error_message = Column(Text, nullable=True)  # Сообщение об ошибке

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    printed_at = Column(DateTime(timezone=True), nullable=True)  # Когда напечатали

    # Relationships
    order = relationship("Order", back_populates="print_jobs")
    order_item = relationship("OrderItem", back_populates="print_jobs")

    def __repr__(self):
        return f"<PrintJob {self.id} ({self.label_type}) - {self.status}>"
