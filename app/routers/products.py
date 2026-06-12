from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Annotated, Optional
from starlette import status
from datetime import datetime
import re

from app.database import SessionLocal
from app.routers.auth import get_current_user
from app.models import Products, Supermarkets

router = APIRouter(
    prefix="/product",
    tags=["product"]
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


def _effective_flyer_dates(product: Products) -> tuple[str | None, str | None]:
    parsed_from, parsed_to = _parse_source_dates(getattr(product, "flyer_source", None))
    return (
        getattr(product, "flyer_valid_from", None) or parsed_from,
        getattr(product, "flyer_valid_to", None) or parsed_to,
    )


def _offer_is_active(product: Products) -> bool:
    _, valid_to = _effective_flyer_dates(product)
    end = _parse_date(valid_to)
    if end is None:
        return True
    return end.date() >= datetime.utcnow().date()


def _serialize_product(product: Products) -> dict:
    data = {
        column.name: getattr(product, column.name)
        for column in product.__table__.columns
    }
    valid_from, valid_to = _effective_flyer_dates(product)
    if valid_from:
        data["flyer_valid_from"] = valid_from
    if valid_to:
        data["flyer_valid_to"] = valid_to

    expired = not _offer_is_active(product)
    data["offer_expired"] = expired
    if expired and data.get("discounted_price") is not None:
        # Do not delete the saved discount from the DB; just expose it as inactive.
        data["expired_discounted_price"] = data.get("discounted_price")
        data["discounted_price"] = None
    return data


class ProductRequest(BaseModel):
    name: str = Field(max_length=100)
    category: str = Field(max_length=100)
    original_price: float = Field(gt=0.0)
    discounted_price: float | None = None
    unit: str = Field(max_length=40)
    supermarket_id: int = Field(gt=0)
    aisle_order: float = Field(ge=0.0)
    image: str | None = None
    calories: float | None = None
    fat: float | None = None
    carbs: float | None = None
    protein: float | None = None
    location: str | None = None

    # Optional flyer/catalog metadata used by the new desktop UI.
    brand: str | None = None
    flyer_page: int | None = None
    flyer_valid_from: str | None = None
    flyer_valid_to: str | None = None
    flyer_source: str | None = None
    flyer_source_url: str | None = None
    is_lidl_plus: bool = False
    flyer_imported_at: str | None = None
    offer_note: str | None = None
    discount_percent: float | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    original_price: float | None = None
    discounted_price: float | None = Field(None, gt=0)
    unit: str | None = None
    supermarket_id: int | None = Field(None, gt=0)
    aisle_order: float | None = None
    image: str | None = None
    calories: float | None = None
    fat: float | None = None
    carbs: float | None = None
    protein: float | None = None
    location: str | None = None

    brand: str | None = None
    flyer_page: int | None = None
    flyer_valid_from: str | None = None
    flyer_valid_to: str | None = None
    flyer_source: str | None = None
    flyer_source_url: str | None = None
    is_lidl_plus: bool | None = None
    flyer_imported_at: str | None = None
    offer_note: str | None = None
    discount_percent: float | None = None


@router.get("", status_code=status.HTTP_200_OK)
async def get_products(
    user: user_dependency,
    db: db_dependency,
    supermarket_id: Optional[int] = Query(default=None, gt=0),
    category: Optional[str] = Query(default=None, max_length=100),
    search: Optional[str] = Query(default=None),
    discounted_only: bool = False,
    lidl_plus_only: bool = False,
    flyer_page: Optional[int] = Query(default=None, gt=0),
):
    product_model = db.query(Products)

    if supermarket_id is not None:
        supermarket = db.query(Supermarkets).filter(Supermarkets.id == supermarket_id).first()
        if supermarket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supermarket not found")
        product_model = product_model.filter(Products.supermarket_id == supermarket_id)

    if category:
        product_model = product_model.filter(Products.category == category)

    if search:
        product_model = product_model.filter(Products.name.ilike(f"%{search}%"))

    if discounted_only:
        product_model = product_model.filter(
            Products.discounted_price.isnot(None),
            Products.discounted_price < Products.original_price,
        )

    if lidl_plus_only and hasattr(Products, "is_lidl_plus"):
        product_model = product_model.filter(Products.is_lidl_plus.is_(True))

    if flyer_page is not None and hasattr(Products, "flyer_page"):
        product_model = product_model.filter(Products.flyer_page == flyer_page)

    return [_serialize_product(product) for product in product_model.all()]


@router.get("/{product_id}", status_code=status.HTTP_200_OK)
async def get_product_by_id(user: user_dependency, db: db_dependency, product_id: int = Path(gt=0)):
    product_model = db.query(Products).filter(Products.id == product_id).first()
    if product_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return _serialize_product(product_model)


@router.get("/supermarket/{supermarket_id}", status_code=status.HTTP_200_OK)
async def get_supermarket_products(user: user_dependency, db: db_dependency, supermarket_id: int = Path(gt=0)):
    supermarket_model = db.query(Supermarkets).filter(Supermarkets.id == supermarket_id).first()
    if supermarket_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supermarket not found")
    products = (
        db.query(Products)
        .filter(Products.supermarket_id == supermarket_id)
        .order_by(Products.aisle_order)
        .all()
    )
    return [_serialize_product(product) for product in products]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(user: user_dependency, db: db_dependency, request: ProductRequest):
    supermarket_model = db.query(Supermarkets).filter(Supermarkets.id == request.supermarket_id).first()
    if supermarket_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supermarket id not found")
    product_model = Products(**request.model_dump())
    db.add(product_model)
    db.commit()
    db.refresh(product_model)
    return product_model


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(user: user_dependency, db: db_dependency, product_id: int = Path(gt=0)):
    product_model = db.query(Products).filter(Products.id == product_id).first()
    if product_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    db.delete(product_model)
    db.commit()


@router.put("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_product(user: user_dependency, db: db_dependency, request: ProductUpdate, product_id: int = Path(gt=0)):
    product_model = db.query(Products).filter(Products.id == product_id).first()
    if product_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product_model, key, value)
    db.commit()
