from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from starlette import status

from app.database import SessionLocal, engine
from app.models import Products, ShoppingHistory, ShoppingHistoryItem, Supermarkets, Users
from app.routers.auth import get_current_user

try:
    from app.services.schema_compat import ensure_schema_compat
except Exception:
    ensure_schema_compat = None


router = APIRouter(prefix="/admin/history", tags=["admin-history"])
_schema_checked = False


def ensure_schema_ready() -> None:
    global _schema_checked
    if not _schema_checked and ensure_schema_compat is not None:
        ensure_schema_compat(engine)
        _schema_checked = True


def get_db():
    ensure_schema_ready()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def require_admin(user: dict) -> None:
    if not user or user.get("user_role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


def model_columns(model) -> set[str]:
    return {column.name for column in model.__table__.columns}


def safe_model_data(model, data: dict) -> dict:
    cols = model_columns(model)
    return {key: value for key, value in data.items() if key in cols}


def assign_known_fields(instance, data: dict) -> None:
    cols = model_columns(instance.__class__)
    for key, value in data.items():
        if key in cols:
            setattr(instance, key, value)


def round_money(value: float | int | None) -> float:
    return round(float(value or 0), 2)


def line_total(item: ShoppingHistoryItem) -> float:
    final_price = getattr(item, "final_price_paid", None)
    if final_price is not None:
        return round_money(final_price)
    return round_money(float(item.price_paid or 0) * int(item.quantity or 1))


def recalculate_history(db: Session, history: ShoppingHistory) -> ShoppingHistory:
    items = db.query(ShoppingHistoryItem).filter(ShoppingHistoryItem.history_id == history.id).all()
    history.total_items = sum(int(item.quantity or 1) for item in items)
    history.total_price = round_money(sum(line_total(item) for item in items))
    db.commit()
    db.refresh(history)
    return history


def serialize_user(user: Users, histories_count: int = 0, total_spent: float = 0) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "histories_count": histories_count,
        "history_total_spent": round_money(total_spent),
    }


def serialize_history(history: ShoppingHistory, user: Users | None = None, preview: list[ShoppingHistoryItem] | None = None) -> dict:
    return {
        "id": history.id,
        "user_id": history.user_id,
        "username": user.username if user else None,
        "email": user.email if user else None,
        "created_at": history.created_at,
        "total_items": history.total_items,
        "total_price": round_money(history.total_price),
        "preview_items": [serialize_item(item) for item in (preview or [])],
    }


def serialize_item(item: ShoppingHistoryItem) -> dict:
    data = {column.name: getattr(item, column.name, None) for column in item.__table__.columns}
    data["line_total"] = line_total(item)
    return data


class AdminHistoryPatch(BaseModel):
    created_at: Optional[str] = None
    total_items: Optional[int] = Field(default=None, ge=0)
    total_price: Optional[float] = Field(default=None, ge=0)
    recalculate: bool = False


class AdminHistoryItemIn(BaseModel):
    product_id: Optional[int] = None
    name: str = Field(min_length=1, max_length=180)
    image: Optional[str] = None
    unit: Optional[str] = None
    price_paid: float = Field(ge=0)
    was_discounted: bool = False
    quantity: int = Field(default=1, gt=0)
    category: Optional[str] = None
    aisle_order: Optional[float] = None
    supermarket_id: Optional[int] = None
    supermarket_name: Optional[str] = None
    calories: Optional[float] = None
    fat: Optional[float] = None
    carbs: Optional[float] = None
    protein: Optional[float] = None

    # variable price fields from v20
    price_type: Optional[str] = Field(default=None, pattern="^(fixed|weight|manual)$")
    price_unit: Optional[str] = None
    estimated_weight: Optional[float] = Field(default=None, ge=0)
    actual_weight: Optional[float] = Field(default=None, ge=0)
    weight_bought: Optional[float] = Field(default=None, ge=0)
    price_per_unit_snapshot: Optional[float] = Field(default=None, ge=0)
    final_price_paid: Optional[float] = Field(default=None, ge=0)
    was_manual_price: Optional[bool] = None
    manual_price: Optional[float] = Field(default=None, ge=0)


class AdminHistoryItemPatch(BaseModel):
    product_id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=180)
    image: Optional[str] = None
    unit: Optional[str] = None
    price_paid: Optional[float] = Field(default=None, ge=0)
    was_discounted: Optional[bool] = None
    quantity: Optional[int] = Field(default=None, gt=0)
    category: Optional[str] = None
    aisle_order: Optional[float] = None
    supermarket_id: Optional[int] = None
    supermarket_name: Optional[str] = None
    calories: Optional[float] = None
    fat: Optional[float] = None
    carbs: Optional[float] = None
    protein: Optional[float] = None

    # variable price fields from v20
    price_type: Optional[str] = Field(default=None, pattern="^(fixed|weight|manual)$")
    price_unit: Optional[str] = None
    estimated_weight: Optional[float] = Field(default=None, ge=0)
    actual_weight: Optional[float] = Field(default=None, ge=0)
    weight_bought: Optional[float] = Field(default=None, ge=0)
    price_per_unit_snapshot: Optional[float] = Field(default=None, ge=0)
    final_price_paid: Optional[float] = Field(default=None, ge=0)
    was_manual_price: Optional[bool] = None
    manual_price: Optional[float] = Field(default=None, ge=0)


@router.get("/debug")
def debug_admin_history(user: user_dependency):
    require_admin(user)
    return {
        "shopping_history_columns": sorted(model_columns(ShoppingHistory)),
        "shopping_history_item_columns": sorted(model_columns(ShoppingHistoryItem)),
        "has_final_price_paid": "final_price_paid" in model_columns(ShoppingHistoryItem),
        "has_weight_bought": "weight_bought" in model_columns(ShoppingHistoryItem),
    }


@router.get("/users")
def list_users_with_history(
    user: user_dependency,
    db: db_dependency,
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=200, gt=1, le=500),
):
    require_admin(user)
    query = db.query(Users)
    if search:
        query = query.filter(or_(Users.username.ilike(f"%{search}%"), Users.email.ilike(f"%{search}%")))

    users = query.order_by(Users.id.desc()).limit(limit).all()
    result = []
    for target in users:
        histories = db.query(ShoppingHistory).filter(ShoppingHistory.user_id == target.id).all()
        result.append(serialize_user(target, len(histories), sum(float(h.total_price or 0) for h in histories)))
    return result


@router.get("/user/{user_id}")
def list_user_histories(
    user: user_dependency,
    db: db_dependency,
    user_id: int = Path(gt=0),
    limit: int = Query(default=100, gt=1, le=500),
):
    require_admin(user)
    target = db.query(Users).filter(Users.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    histories = (
        db.query(ShoppingHistory)
        .filter(ShoppingHistory.user_id == user_id)
        .order_by(ShoppingHistory.created_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for history in histories:
        preview = (
            db.query(ShoppingHistoryItem)
            .filter(ShoppingHistoryItem.history_id == history.id)
            .limit(5)
            .all()
        )
        result.append(serialize_history(history, target, preview))
    return result


@router.get("/{history_id}")
def get_history(user: user_dependency, db: db_dependency, history_id: int = Path(gt=0)):
    require_admin(user)
    history = db.query(ShoppingHistory).filter(ShoppingHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
    target = db.query(Users).filter(Users.id == history.user_id).first()
    preview = db.query(ShoppingHistoryItem).filter(ShoppingHistoryItem.history_id == history.id).all()
    return serialize_history(history, target, preview)


@router.put("/{history_id}")
def update_history(user: user_dependency, db: db_dependency, request: AdminHistoryPatch, history_id: int = Path(gt=0)):
    require_admin(user)
    history = db.query(ShoppingHistory).filter(ShoppingHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")

    data = request.model_dump(exclude_unset=True)
    recalc = bool(data.pop("recalculate", False))
    assign_known_fields(history, data)

    db.commit()
    db.refresh(history)

    if recalc:
        history = recalculate_history(db, history)
    return serialize_history(history)


@router.delete("/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history(user: user_dependency, db: db_dependency, history_id: int = Path(gt=0)):
    require_admin(user)
    history = db.query(ShoppingHistory).filter(ShoppingHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
    db.query(ShoppingHistoryItem).filter(ShoppingHistoryItem.history_id == history.id).delete(synchronize_session=False)
    db.delete(history)
    db.commit()


@router.get("/{history_id}/items")
def list_history_items(user: user_dependency, db: db_dependency, history_id: int = Path(gt=0)):
    require_admin(user)
    history = db.query(ShoppingHistory).filter(ShoppingHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
    items = db.query(ShoppingHistoryItem).filter(ShoppingHistoryItem.history_id == history_id).order_by(ShoppingHistoryItem.id.asc()).all()
    return [serialize_item(item) for item in items]


@router.post("/{history_id}/items", status_code=status.HTTP_201_CREATED)
def create_history_item(user: user_dependency, db: db_dependency, request: AdminHistoryItemIn, history_id: int = Path(gt=0)):
    require_admin(user)
    history = db.query(ShoppingHistory).filter(ShoppingHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")

    data = request.model_dump()
    data["history_id"] = history_id

    if data.get("product_id"):
        product = db.query(Products).filter(Products.id == data["product_id"]).first()
        if product:
            data.setdefault("name", product.name)
            data["image"] = data.get("image") or product.image
            data["unit"] = data.get("unit") or product.unit
            data["category"] = data.get("category") or product.category
            data["aisle_order"] = data.get("aisle_order") if data.get("aisle_order") is not None else product.aisle_order
            data["supermarket_id"] = data.get("supermarket_id") or product.supermarket_id
            data["supermarket_name"] = data.get("supermarket_name") or (product.supermarket.name if product.supermarket else None)

    item = ShoppingHistoryItem(**safe_model_data(ShoppingHistoryItem, data))
    db.add(item)
    db.commit()
    db.refresh(item)
    recalculate_history(db, history)
    return serialize_item(item)


@router.put("/items/{item_id}")
def update_history_item(user: user_dependency, db: db_dependency, request: AdminHistoryItemPatch, item_id: int = Path(gt=0)):
    require_admin(user)
    item = db.query(ShoppingHistoryItem).filter(ShoppingHistoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="History item not found")

    data = request.model_dump(exclude_unset=True)
    assign_known_fields(item, data)
    db.commit()
    db.refresh(item)

    history = db.query(ShoppingHistory).filter(ShoppingHistory.id == item.history_id).first()
    if history:
        recalculate_history(db, history)
    return serialize_item(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_item(user: user_dependency, db: db_dependency, item_id: int = Path(gt=0)):
    require_admin(user)
    item = db.query(ShoppingHistoryItem).filter(ShoppingHistoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="History item not found")
    history_id = item.history_id
    db.delete(item)
    db.commit()
    history = db.query(ShoppingHistory).filter(ShoppingHistory.id == history_id).first()
    if history:
        recalculate_history(db, history)


@router.post("/{history_id}/recalculate")
def recalc_history(user: user_dependency, db: db_dependency, history_id: int = Path(gt=0)):
    require_admin(user)
    history = db.query(ShoppingHistory).filter(ShoppingHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
    history = recalculate_history(db, history)
    return serialize_history(history)
