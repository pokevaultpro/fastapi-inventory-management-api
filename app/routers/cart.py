from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette import status

from app.database import SessionLocal, engine
from app.routers.auth import get_current_user
from app.models import Cart, Products, Supermarkets, ShoppingHistory, ShoppingHistoryItem

try:
    from app.services.schema_compat import ensure_schema_compat
except Exception:
    ensure_schema_compat = None


router = APIRouter(prefix="/cart", tags=["cart"])
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


class CartRequest(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, gt=0)
    checked: bool = False
    estimated_weight: Optional[float] = Field(default=None, ge=0)
    actual_weight: Optional[float] = Field(default=None, ge=0)
    manual_price: Optional[float] = Field(default=None, ge=0)


class CartUpdate(BaseModel):
    quantity: Optional[int] = Field(default=None, gt=0)
    checked: Optional[bool] = Field(default=None)
    estimated_weight: Optional[float] = Field(default=None, ge=0)
    actual_weight: Optional[float] = Field(default=None, ge=0)
    manual_price: Optional[float] = Field(default=None, ge=0)


def model_columns(model) -> set[str]:
    return {col.name for col in model.__table__.columns}


def safe_model_data(model, data: dict) -> dict:
    available = model_columns(model)
    return {k: v for k, v in data.items() if k in available}


def assign_known_fields(instance, data: dict) -> None:
    available = model_columns(instance.__class__)
    for key, value in data.items():
        if key in available:
            setattr(instance, key, value)


def parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")[:10])
    except ValueError:
        return None


def offer_is_active(product: Products) -> bool:
    valid_to = getattr(product, "flyer_valid_to", None)
    if not valid_to:
        return True
    end = parse_date(valid_to)
    if not end:
        return True
    return end.date() >= datetime.utcnow().date()


def has_discount(product: Products) -> bool:
    original = float(getattr(product, "original_price", 0) or 0)
    discounted = getattr(product, "discounted_price", None)
    if discounted is None:
        return False
    discounted = float(discounted or 0)
    return original > 0 and discounted > 0 and discounted < original and offer_is_active(product)


def base_unit_price(product: Products) -> float:
    if has_discount(product):
        return float(product.discounted_price or 0)
    return float(getattr(product, "original_price", 0) or 0)


def product_price_type(product: Products) -> str:
    value = getattr(product, "price_type", None) or "fixed"
    value = str(value).lower()
    return value if value in {"fixed", "weight", "manual"} else "fixed"


def product_price_unit(product: Products) -> str:
    return getattr(product, "price_unit", None) or getattr(product, "unit", None) or "pz"


def line_weight(item: Cart) -> float | None:
    value = getattr(item, "actual_weight", None)
    if value is None:
        value = getattr(item, "estimated_weight", None)
    if value is None:
        return None
    return float(value or 0)


def line_total(item: Cart) -> float:
    manual_price = getattr(item, "manual_price", None)
    if manual_price is not None:
        return round(float(manual_price or 0), 2)

    product = item.product
    ptype = product_price_type(product)
    price = base_unit_price(product)

    if ptype == "weight":
        weight = line_weight(item)
        if weight is None:
            weight = float(item.quantity or 1)
        return round(price * weight, 2)

    return round(price * int(item.quantity or 1), 2)


def history_price_paid(item: Cart) -> float:
    qty = int(item.quantity or 1)
    if qty <= 0:
        qty = 1
    return round(line_total(item) / qty, 4)


def validate_variable_item_for_finalize(item: Cart) -> None:
    product = item.product
    ptype = product_price_type(product)
    base_price = base_unit_price(product)
    manual_price = getattr(item, "manual_price", None)

    if ptype == "manual" and manual_price is None and base_price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inserisci il prezzo finale per '{product.name}' prima di finalizzare.",
        )

    if ptype == "weight" and base_price <= 0 and manual_price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inserisci prezzo finale o prezzo al kg valido per '{product.name}'.",
        )


@router.get("", status_code=status.HTTP_200_OK)
async def read_cart(user: user_dependency, db: db_dependency, supermarket_id: Optional[int] = Query(default=None, gt=0)):
    query = db.query(Cart).filter(Cart.owner_id == user.get("id"))
    if supermarket_id is not None:
        supermarket_model = db.query(Supermarkets).filter(Supermarkets.id == supermarket_id).first()
        if supermarket_model is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supermarket not found")
        query = query.join(Products).filter(Products.supermarket_id == supermarket_id)
    return query.all()


@router.get("/{cart_id}", status_code=status.HTTP_200_OK)
async def read_cart_by_id(user: user_dependency, db: db_dependency, cart_id: int = Path(gt=0)):
    cart_model = db.query(Cart).filter(Cart.id == cart_id).filter(Cart.owner_id == user.get("id")).first()
    if cart_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    return cart_model


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_cart(user: user_dependency, db: db_dependency, cart_request: CartRequest):
    product_model = db.query(Products).filter(Products.id == cart_request.product_id).first()
    if not product_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    existing = (
        db.query(Cart)
        .filter(Cart.product_id == cart_request.product_id)
        .filter(Cart.owner_id == user.get("id"))
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product already in cart")

    data = cart_request.model_dump()
    if product_price_type(product_model) == "weight" and data.get("estimated_weight") is None:
        data["estimated_weight"] = 1.0

    cart = Cart(**safe_model_data(Cart, data), owner_id=user.get("id"))
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return cart


@router.put("/{cart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_cart(user: user_dependency, db: db_dependency, cart_update: CartUpdate, cart_id: int = Path(gt=0)):
    cart_model = db.query(Cart).filter(Cart.id == cart_id).filter(Cart.owner_id == user.get("id")).first()
    if cart_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

    data = cart_update.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You must update at least one field")

    assign_known_fields(cart_model, data)
    db.commit()


@router.post("/finalize", status_code=status.HTTP_201_CREATED)
async def create_shopping_history(user: user_dependency, db: db_dependency):
    owner_id = user.get("id")
    cart_model = (
        db.query(Cart)
        .filter(Cart.owner_id == owner_id)
        .filter(Cart.checked == True)
        .all()
    )
    if not cart_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The cart is empty!")

    for item in cart_model:
        validate_variable_item_for_finalize(item)

    created_at = datetime.utcnow().isoformat()
    total_items = sum(int(item.quantity or 1) for item in cart_model)
    total_price = round(sum(line_total(item) for item in cart_model), 2)

    shopping_history_model = ShoppingHistory(
        total_items=total_items,
        total_price=total_price,
        user_id=owner_id,
        created_at=created_at,
    )
    db.add(shopping_history_model)
    db.commit()
    db.refresh(shopping_history_model)

    for item in cart_model:
        product = item.product
        ptype = product_price_type(product)
        price_unit = product_price_unit(product)
        weight = line_weight(item)
        final_total = line_total(item)
        data = {
            "history_id": shopping_history_model.id,
            "product_id": product.id,
            "name": product.name,
            "image": product.image,
            "unit": product.unit,
            "price_paid": history_price_paid(item),
            "was_discounted": has_discount(product),
            "quantity": int(item.quantity or 1),
            "category": product.category,
            "aisle_order": product.aisle_order,
            "supermarket_id": product.supermarket_id,
            "supermarket_name": product.supermarket.name if product.supermarket else None,
            "calories": product.calories,
            "fat": product.fat,
            "carbs": product.carbs,
            "protein": product.protein,
            "price_type": ptype,
            "price_unit": price_unit,
            "estimated_weight": getattr(item, "estimated_weight", None),
            "actual_weight": getattr(item, "actual_weight", None),
            "weight_bought": weight if ptype == "weight" else None,
            "price_per_unit_snapshot": base_unit_price(product),
            "final_price_paid": final_total,
            "was_manual_price": getattr(item, "manual_price", None) is not None,
            "manual_price": getattr(item, "manual_price", None),
        }

        shopping_history_item_model = ShoppingHistoryItem(**safe_model_data(ShoppingHistoryItem, data))
        db.add(shopping_history_item_model)

    db.commit()

    db.query(Cart).filter(Cart.owner_id == owner_id).filter(Cart.checked == True).delete(synchronize_session=False)
    db.commit()

    return {
        "message": "Spesa finalizzata con successo",
        "finalized_items": len(cart_model),
        "history_id": shopping_history_model.id,
        "total_price": total_price,
    }


@router.delete("/{cart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart_id(user: user_dependency, db: db_dependency, cart_id: int = Path(gt=0)):
    cart_model = db.query(Cart).filter(Cart.id == cart_id).filter(Cart.owner_id == user.get("id")).first()
    if cart_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    db.delete(cart_model)
    db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart(
    user: user_dependency,
    db: db_dependency,
    supermarket_id: Optional[int] = Query(default=None, gt=0),
    checked: Optional[bool] = Query(default=None),
):
    if supermarket_id is None and checked is None:
        deleted = db.query(Cart).filter(Cart.owner_id == user.get("id")).delete(synchronize_session=False)
        db.commit()
        if deleted == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
        return

    cart_query = db.query(Cart.id).join(Products).filter(Cart.owner_id == user.get("id"))

    if supermarket_id is not None:
        supermarket_model = db.query(Supermarkets).filter(Supermarkets.id == supermarket_id).first()
        if supermarket_model is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supermarket not found")
        cart_query = cart_query.filter(Products.supermarket_id == supermarket_id)

    if checked is not None:
        cart_query = cart_query.filter(Cart.checked == checked)

    deleted = db.query(Cart).filter(Cart.id.in_(cart_query)).delete(synchronize_session=False)
    db.commit()
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
