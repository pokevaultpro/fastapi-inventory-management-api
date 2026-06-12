from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Annotated, Optional
from starlette import status

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

    return product_model.all()


@router.get("/{product_id}", status_code=status.HTTP_200_OK)
async def get_product_by_id(user: user_dependency, db: db_dependency, product_id: int = Path(gt=0)):
    product_model = db.query(Products).filter(Products.id == product_id).first()
    if product_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product_model


@router.get("/supermarket/{supermarket_id}", status_code=status.HTTP_200_OK)
async def get_supermarket_products(user: user_dependency, db: db_dependency, supermarket_id: int = Path(gt=0)):
    supermarket_model = db.query(Supermarkets).filter(Supermarkets.id == supermarket_id).first()
    if supermarket_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supermarket not found")
    return (
        db.query(Products)
        .filter(Products.supermarket_id == supermarket_id)
        .order_by(Products.aisle_order)
        .all()
    )


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
