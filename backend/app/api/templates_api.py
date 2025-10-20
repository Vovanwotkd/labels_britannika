"""
Templates API
Управление шаблонами этикеток
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Template
from app.api.auth_api import require_auth, require_admin
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])


# ============================================================================
# SCHEMAS
# ============================================================================

class TemplateConfigSchema(BaseModel):
    """Схема конфигурации шаблона"""
    paper_width_mm: int
    paper_height_mm: int
    paper_gap_mm: int
    shelf_life_hours: int
    logo: Optional[dict] = None
    title: Optional[dict] = None
    weight_calories: Optional[dict] = None
    bju: Optional[dict] = None
    ingredients: Optional[dict] = None
    datetime_shelf: Optional[dict] = None
    barcode: Optional[dict] = None

    class Config:
        extra = "allow"  # Разрешаем дополнительные поля


class TemplateSchema(BaseModel):
    """Схема шаблона"""
    id: int
    name: str
    brand_id: Optional[str]
    is_default: bool
    config: dict
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class TemplateCreateRequest(BaseModel):
    """Запрос на создание шаблона"""
    name: str
    brand_id: Optional[str] = None
    is_default: bool = False
    config: dict


class TemplateUpdateRequest(BaseModel):
    """Запрос на обновление шаблона"""
    name: Optional[str] = None
    brand_id: Optional[str] = None
    is_default: Optional[bool] = None
    config: Optional[dict] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[TemplateSchema])
async def get_all_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Получить все шаблоны

    Требует аутентификации
    """
    templates = db.query(Template).all()
    return templates


@router.get("/{template_id}", response_model=TemplateSchema)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Получить шаблон по ID

    Требует аутентификации
    """
    template = db.query(Template).filter(Template.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.post("/", response_model=TemplateSchema)
async def create_template(
    request: TemplateCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Создать новый шаблон

    Требует прав администратора
    """
    # Проверяем уникальность brand_id
    if request.brand_id:
        existing = db.query(Template).filter(
            Template.brand_id == request.brand_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Template with brand_id '{request.brand_id}' already exists"
            )

    # Если устанавливаем как default, снимаем флаг у других
    if request.is_default:
        db.query(Template).update({"is_default": False})

    template = Template(
        name=request.name,
        brand_id=request.brand_id,
        is_default=request.is_default,
        config=request.config,
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    logger.info(f"➕ Template created: {template.name} (id={template.id})")

    return template


@router.put("/{template_id}", response_model=TemplateSchema)
async def update_template(
    template_id: int,
    request: TemplateUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Обновить шаблон

    Требует прав администратора
    """
    template = db.query(Template).filter(Template.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Обновляем поля
    if request.name is not None:
        template.name = request.name

    if request.brand_id is not None:
        # Проверяем уникальность brand_id
        existing = db.query(Template).filter(
            Template.brand_id == request.brand_id,
            Template.id != template_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Template with brand_id '{request.brand_id}' already exists"
            )
        template.brand_id = request.brand_id

    if request.is_default is not None:
        if request.is_default:
            # Снимаем флаг default у других шаблонов
            db.query(Template).filter(Template.id != template_id).update(
                {"is_default": False}
            )
        template.is_default = request.is_default

    if request.config is not None:
        template.config = request.config

    db.commit()
    db.refresh(template)

    logger.info(f"📝 Template updated: {template.name} (id={template.id})")

    return template


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Удалить шаблон

    Требует прав администратора
    Нельзя удалить шаблон по умолчанию
    """
    template = db.query(Template).filter(Template.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.is_default:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete default template"
        )

    db.delete(template)
    db.commit()

    logger.info(f"🗑️  Template deleted: {template.name} (id={template.id})")

    return {
        "success": True,
        "message": f"Template '{template.name}' deleted"
    }


@router.post("/{template_id}/set-default")
async def set_default_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Установить шаблон по умолчанию

    Требует прав администратора
    """
    template = db.query(Template).filter(Template.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Снимаем флаг default у всех шаблонов
    db.query(Template).update({"is_default": False})

    # Устанавливаем флаг для выбранного шаблона
    template.is_default = True
    db.commit()
    db.refresh(template)

    logger.info(f"⭐ Default template set: {template.name} (id={template.id})")

    return {
        "success": True,
        "message": f"Template '{template.name}' set as default",
        "template": TemplateSchema.from_orm(template)
    }


@router.post("/{template_id}/test-print")
async def test_print_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Тестовая печать шаблона

    Печатает тестовую этикетку с примером данных
    Требует прав администратора
    """
    from app.models import PrintJob
    from app.services.printer.tspl_renderer import TSPLRenderer

    template = db.query(Template).filter(Template.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Тестовые данные блюда
    test_dish_data = {
        "name": "ТЕСТОВОЕ БЛЮДО",
        "rk_code": "TEST123",
        "weight_g": 250,
        "calories": 350,
        "protein": 15.5,
        "fat": 12.3,
        "carbs": 45.2,
        "ingredients": ["Тестовый ингредиент 1", "Тестовый ингредиент 2", "Тестовый ингредиент 3"],
        "label_type": "MAIN"
    }

    try:
        # Генерируем TSPL команды
        renderer = TSPLRenderer(template.config)
        tspl_code = renderer.render(test_dish_data)

        # Создаём print job
        print_job = PrintJob(
            order_id=None,  # Нет привязки к заказу
            order_item_id=None,
            dish_name="TEST: " + template.name,
            dish_code="TEST",
            quantity=1,
            label_type="MAIN",
            tspl_code=tspl_code,
            status="QUEUED",
        )

        db.add(print_job)
        db.commit()
        db.refresh(print_job)

        logger.info(f"🖨️  Test print job created for template: {template.name} (id={template.id})")

        return {
            "success": True,
            "message": f"Test print queued for template '{template.name}'",
            "print_job_id": print_job.id
        }

    except Exception as e:
        logger.error(f"❌ Failed to create test print job: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create test print: {str(e)}"
        )
