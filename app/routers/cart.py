from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Annotated, Optional
from starlette import status
from datetime import datetime
import re

from app.database import SessionLocal
from app.routers import shopping_history_item
from app.routers.auth import get_current_user
from app.models import Cart, Products, Supermarkets, ShoppingHistory, ShoppingHistoryItem

router = APIRouter(
    prefix="/cart",
    tags=["cart"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")[:10])
    except ValueError:
        return None


def _parse_source_dates(value: str | None) -> tuple[str | None, str | None]:
    text = str(value or "")
    match = re.search(r"(\d{4})[_-](\d{2})[_-](\d{2}).*?(\d{4})[_-](\d{2})[_-](\d{2})", text)
    if not match:
        return None, None
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}", f"{match.group(4)}-{match.group(5)}-{match.group(6)}"


def _effective_flyer_to(product: Products) -> str | None:
    valid_to = getattr(product, "flyer_valid_to", None)
    if valid_to:
        return valid_to
    _, parsed_to = _parse_source_dates(getattr(product, "flyer_source", None))
    return parsed_to


def _offer_is_active(product: Products) -> bool:
    end = _parse_date(_effective_flyer_to(product))
    if end is None:
        return True
    return end.date() >= datetime.utcnow().date()


def _product_current_price(product: Products) -> float:
    if _offer_is_active(product) and product.discounted_price is not None:
        return float(product.discounted_price)
    return float(product.original_price)


def _product_is_discounted_now(product: Products) -> bool:
    return _offer_is_active(product) and product.discounted_price is not None and product.discounted_price < product.original_price

class CartRequest(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    checked: bool = False

class CartUpdate(BaseModel):
    quantity: Optional[int] = Field(default=None, gt=0)
    checked: Optional[bool] = Field(default=None)

"""
@router.get("", status_code=status.HTTP_200_OK)
async def read_cart_of_everybody(user: user_dependency, db: db_dependency, supermarket_id: Optional[int] = Query(default=None, gt=0)):
    if supermarket_id is not None:
        supermarket_model = db.query(Supermarkets).filter(Supermarkets.id == supermarket_id).first()
        if supermarket_model is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supermarket not found")
        cart_model = db.query(Cart).join(Products).filter(Products.supermarket_id == supermarket_id).all()
        return cart_model
    return db.query(Cart).all()
"""

@router.get("", status_code=status.HTTP_200_OK)
async def read_cart(user: user_dependency, db: db_dependency, supermarket_id: Optional[int] = Query(default=None, gt=0)):
    if supermarket_id is not None:
        supermarket_model = db.query(Supermarkets).filter(Supermarkets.id == supermarket_id).first()
        if supermarket_model is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supermarket not found")
        cart_model = (db.query(Cart).join(Products).filter(Products.supermarket_id == supermarket_id)
                      .filter(Cart.owner_id == user.get('id')).all())
        return cart_model
    return db.query(Cart).filter(Cart.owner_id == user.get('id')).all()

@router.get("/{cart_id}", status_code=status.HTTP_200_OK)
async def read_cart_by_id(user: user_dependency, db: db_dependency, cart_id: int = Path(gt=0)):
        cart_model = db.query(Cart).filter(Cart.id == cart_id).filter(Cart.owner_id == user.get('id')).first()
        if cart_model is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
        return cart_model

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_cart(user: user_dependency, db: db_dependency, cart_request: CartRequest):
    product_model = db.query(Products).filter(Products.id == cart_request.product_id).first()
    if not product_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    existing = (db.query(Cart).filter(Cart.product_id == cart_request.product_id)
                .filter(Cart.owner_id == user.get('id')).first())
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product already in cart")
    cart = Cart(**cart_request.model_dump(), owner_id=user.get('id'))
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return cart

@router.post("/finalize", status_code=status.HTTP_201_CREATED)
async def create_shopping_history(user: user_dependency, db: db_dependency):
    owner_id = user.get("id")
    cart_model = db.query(Cart).filter(Cart.owner_id == owner_id).filter(Cart.checked == True).all()
    if not cart_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The cart is empty!")
    created_at = datetime.utcnow().isoformat()
    total_items = sum(item.quantity for item in cart_model)
    total_price = sum(_product_current_price(item.product) * item.quantity for item in cart_model)
    shopping_history_model = ShoppingHistory(total_items=total_items, total_price=total_price,
                                             user_id=owner_id, created_at=created_at)
    db.add(shopping_history_model)
    db.commit()
    db.refresh(shopping_history_model)

    for item in cart_model:
        product = item.product
        price_paid = _product_current_price(product)
        was_discounted = _product_is_discounted_now(product)

        shopping_history_item_model = ShoppingHistoryItem(
            history_id=shopping_history_model.id,
            product_id=product.id,
            name=product.name,
            image=product.image,
            unit=product.unit,
            price_paid=price_paid,
            was_discounted=was_discounted,
            quantity = item.quantity,
            category=product.category,
            aisle_order = product.aisle_order,
            supermarket_id = product.supermarket_id,
            supermarket_name = product.supermarket.name,
            calories = product.calories,
            fat = product.fat,
            carbs = product.carbs,
            protein = product.protein,
        )
        db.add(shopping_history_item_model)
    db.commit()


    db.query(Cart).filter(Cart.owner_id == owner_id).filter(Cart.checked == True).delete()
    db.commit()

    return {
        "message": "Spesa finalizzata con successo",
        "finalized_items": len(cart_model),
        "history_id": shopping_history_model.id
    }


@router.put("/{cart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_cart(user: user_dependency, db: db_dependency, cart_update: CartUpdate, cart_id: int = Path(gt=0)):
    cart_model = db.query(Cart).filter(Cart.id == cart_id).filter(Cart.owner_id == user.get('id')).first()
    if cart_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    if cart_update.checked is None and cart_update.quantity is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You must update at least one field")
    if cart_update.quantity is not None:
        cart_model.quantity = cart_update.quantity
    if cart_update.checked is not None:
        cart_model.checked = cart_update.checked
    db.commit()

@router.delete("/{cart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart_id(user: user_dependency, db: db_dependency, cart_id: int = Path(gt=0)):
    cart_model = db.query(Cart).filter(Cart.id == cart_id).filter(Cart.owner_id == user.get('id')).first()
    if cart_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    db.delete(cart_model)
    db.commit()

@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart(user: user_dependency, db: db_dependency, supermarket_id: Optional[int] = Query(default=None, gt=0), checked: Optional[bool] = Query(default=None)):
    if supermarket_id is None and checked is None:
        deleted = db.query(Cart).filter(Cart.owner_id == user.get('id')).delete(synchronize_session=False)
        db.commit()
        if deleted == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
        return
    cart_model = db.query(Cart.id).join(Products).filter(Cart.owner_id == user.get('id'))
    if supermarket_id is not None:
        supermarket_model = db.query(Supermarkets).filter(Supermarkets.id == supermarket_id).first()
        if supermarket_model is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supermarket not found")
        cart_model = cart_model.filter(Products.supermarket_id == supermarket_id)
    if checked is not None:
        cart_model = cart_model.filter(Cart.checked == checked)
    deleted = db.query(Cart).filter(Cart.id.in_(cart_model)).delete(synchronize_session=False)
    db.commit()
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
