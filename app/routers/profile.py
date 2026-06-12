from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette import status

from app.database import SessionLocal, engine
from app.models import Cart, Favorites, Products, RecipeItems, Recipes, ShoppingHistory, ShoppingHistoryItem, Users
from app.routers.auth import get_current_user
from app.services.schema_compat import ensure_schema_compat

router = APIRouter(prefix="/profile", tags=["profile"])

_schema_checked = False


def ensure_schema_ready() -> None:
    global _schema_checked
    if not _schema_checked:
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


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, max_length=80)
    last_name: Optional[str] = Field(default=None, max_length=80)
    username: Optional[str] = Field(default=None, max_length=80)


def _parse_date(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")[:10])
    except Exception:
        return None


def _offer_is_active(product: Products) -> bool:
    valid_to = getattr(product, "flyer_valid_to", None)
    end = _parse_date(valid_to)
    if end is None:
        return True
    return end.date() >= datetime.utcnow().date()


def _current_price(product: Products | None) -> float:
    if product is None:
        return 0.0
    original = float(product.original_price or 0)
    discounted = product.discounted_price
    if discounted is not None and float(discounted) < original and _offer_is_active(product):
        return float(discounted)
    return original


def _history_stats(db: Session, user_id: int) -> dict:
    histories = (
        db.query(ShoppingHistory)
        .filter(ShoppingHistory.user_id == user_id)
        .order_by(ShoppingHistory.created_at.desc())
        .all()
    )
    total_spent = sum(float(h.total_price or 0) for h in histories)
    total_items = sum(int(h.total_items or 0) for h in histories)
    avg_trip = total_spent / len(histories) if histories else 0
    latest = histories[:5]
    return {
        "trips_count": len(histories),
        "total_spent": round(total_spent, 2),
        "total_items": total_items,
        "avg_trip": round(avg_trip, 2),
        "latest": [
            {
                "id": h.id,
                "created_at": h.created_at,
                "total_price": h.total_price,
                "total_items": h.total_items,
            }
            for h in latest
        ],
    }


@router.get("/summary", status_code=status.HTTP_200_OK)
def get_profile_summary(user: user_dependency, db: db_dependency):
    user_id = user.get("id")
    user_model = db.query(Users).filter(Users.id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    cart_items = db.query(Cart).filter(Cart.owner_id == user_id).all()
    cart_total = sum(_current_price(item.product) * int(item.quantity or 1) for item in cart_items if item.product)
    favorites_count = db.query(Favorites).filter(Favorites.owner_id == user_id).count()
    recipes_count = db.query(Recipes).filter(Recipes.owner_id == user_id).count()
    products_count = db.query(Products).count()

    top_categories_rows = (
        db.query(ShoppingHistoryItem.category, func.sum(ShoppingHistoryItem.quantity).label("qty"))
        .join(ShoppingHistory, ShoppingHistory.id == ShoppingHistoryItem.history_id)
        .filter(ShoppingHistory.user_id == user_id)
        .group_by(ShoppingHistoryItem.category)
        .order_by(func.sum(ShoppingHistoryItem.quantity).desc())
        .limit(5)
        .all()
    )

    return {
        "user": {
            "id": user_model.id,
            "email": user_model.email,
            "username": user_model.username,
            "first_name": user_model.first_name,
            "last_name": user_model.last_name,
            "role": user_model.role,
            "is_active": user_model.is_active,
        },
        "cart": {
            "items_count": len(cart_items),
            "total_quantity": sum(int(item.quantity or 1) for item in cart_items),
            "estimated_total": round(cart_total, 2),
        },
        "library": {
            "favorites_count": favorites_count,
            "recipes_count": recipes_count,
            "products_count": products_count,
        },
        "history": _history_stats(db, user_id),
        "top_categories": [
            {"category": category or "Altro", "quantity": int(qty or 0)}
            for category, qty in top_categories_rows
        ],
    }


@router.put("", status_code=status.HTTP_200_OK)
def update_profile(user: user_dependency, db: db_dependency, request: ProfileUpdate):
    user_id = user.get("id")
    user_model = db.query(Users).filter(Users.id == user_id).first()
    if not user_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_username = (request.username or "").strip()
    if new_username and new_username != user_model.username:
        existing = db.query(Users).filter(Users.username == new_username).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username già esistente")
        user_model.username = new_username

    if request.first_name is not None:
        user_model.first_name = request.first_name.strip()
    if request.last_name is not None:
        user_model.last_name = request.last_name.strip()

    db.commit()
    db.refresh(user_model)
    return {
        "id": user_model.id,
        "email": user_model.email,
        "username": user_model.username,
        "first_name": user_model.first_name,
        "last_name": user_model.last_name,
    }
