from __future__ import annotations

from typing import Annotated, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from starlette import status

from app.database import SessionLocal, engine
from app.models import (
    Cart,
    Favorites,
    Products,
    RecipeItems,
    Recipes,
    ShoppingHistoryItem,
    Supermarkets,
    Users,
)
from app.routers.auth import get_current_user
from app.services.schema_compat import ensure_schema_compat

router = APIRouter(prefix="/admin", tags=["admin"])

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


def require_admin(user: dict) -> None:
    if not user or user.get("user_role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


def product_price(product: Products) -> float:
    discounted = product.discounted_price
    if discounted is not None and product.original_price is not None and discounted < product.original_price:
        return float(discounted)
    return float(product.original_price or 0)


def serialize_product(product: Products) -> dict:
    return {
        column.name: getattr(product, column.name)
        for column in product.__table__.columns
    } | {
        "current_price": product_price(product),
        "supermarket_name": product.supermarket.name if getattr(product, "supermarket", None) else None,
    }


def serialize_supermarket(sm: Supermarkets) -> dict:
    return {
        "id": sm.id,
        "name": sm.name,
        "image": sm.image,
        "location": sm.location,
        "products_count": len(sm.products or []),
    }


def serialize_user(user: Users) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "role": user.role,
    }


def serialize_recipe(db: Session, recipe: Recipes) -> dict:
    owner = db.query(Users).filter(Users.id == recipe.owner_id).first()
    items_count = db.query(RecipeItems).filter(RecipeItems.recipe_id == recipe.id).count()
    return {
        "id": recipe.id,
        "name": recipe.name,
        "image": recipe.image,
        "owner_id": recipe.owner_id,
        "owner_username": owner.username if owner else None,
        "description": getattr(recipe, "description", None),
        "servings": getattr(recipe, "servings", None) or 1,
        "prep_time_minutes": getattr(recipe, "prep_time_minutes", None),
        "instructions": getattr(recipe, "instructions", None),
        "source_type": getattr(recipe, "source_type", None) or "personal",
        "created_at": getattr(recipe, "created_at", None),
        "items_count": items_count,
    }


class AdminProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(default="Altro", max_length=100)
    original_price: float = Field(gt=0)
    discounted_price: Optional[float] = Field(default=None, gt=0)
    unit: str = Field(default="pz", max_length=60)
    supermarket_id: int = Field(gt=0)
    aisle_order: float = 999
    image: Optional[str] = None
    calories: Optional[float] = None
    fat: Optional[float] = None
    carbs: Optional[float] = None
    protein: Optional[float] = None
    location: Optional[str] = None
    brand: Optional[str] = None
    flyer_page: Optional[int] = None
    flyer_valid_from: Optional[str] = None
    flyer_valid_to: Optional[str] = None
    is_lidl_plus: bool = False
    offer_note: Optional[str] = None
    discount_percent: Optional[float] = None


class AdminProductPatch(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    original_price: Optional[float] = Field(default=None, gt=0)
    discounted_price: Optional[float] = Field(default=None, gt=0)
    unit: Optional[str] = None
    supermarket_id: Optional[int] = Field(default=None, gt=0)
    aisle_order: Optional[float] = None
    image: Optional[str] = None
    calories: Optional[float] = None
    fat: Optional[float] = None
    carbs: Optional[float] = None
    protein: Optional[float] = None
    location: Optional[str] = None
    brand: Optional[str] = None
    flyer_page: Optional[int] = None
    flyer_valid_from: Optional[str] = None
    flyer_valid_to: Optional[str] = None
    is_lidl_plus: Optional[bool] = None
    offer_note: Optional[str] = None
    discount_percent: Optional[float] = None


class AdminSupermarketIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    image: Optional[str] = None
    location: Optional[str] = None


class AdminUserPatch(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = Field(default=None, pattern="^(user|admin)$")
    is_active: Optional[bool] = None


class AdminRecipeIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    owner_id: int = Field(gt=0)
    image: Optional[str] = None
    description: Optional[str] = None
    servings: Optional[int] = Field(default=1, gt=0)
    prep_time_minutes: Optional[int] = Field(default=None, ge=0)
    instructions: Optional[str] = None


class AdminRecipePatch(BaseModel):
    name: Optional[str] = None
    owner_id: Optional[int] = Field(default=None, gt=0)
    image: Optional[str] = None
    description: Optional[str] = None
    servings: Optional[int] = Field(default=None, gt=0)
    prep_time_minutes: Optional[int] = Field(default=None, ge=0)
    instructions: Optional[str] = None


@router.get("/summary")
def admin_summary(user: user_dependency, db: db_dependency):
    require_admin(user)
    return {
        "products": db.query(Products).count(),
        "supermarkets": db.query(Supermarkets).count(),
        "users": db.query(Users).count(),
        "recipes": db.query(Recipes).count(),
    }


@router.get("/products")
def admin_list_products(
    user: user_dependency,
    db: db_dependency,
    search: Optional[str] = Query(default=None),
    supermarket_id: Optional[int] = Query(default=None),
    limit: int = Query(default=80, gt=1, le=500),
):
    require_admin(user)
    query = db.query(Products)
    if search:
        query = query.filter(or_(Products.name.ilike(f"%{search}%"), Products.category.ilike(f"%{search}%")))
    if supermarket_id:
        query = query.filter(Products.supermarket_id == supermarket_id)
    rows = query.order_by(Products.id.desc()).limit(limit).all()
    return [serialize_product(p) for p in rows]


@router.post("/products", status_code=status.HTTP_201_CREATED)
def admin_create_product(user: user_dependency, db: db_dependency, request: AdminProductIn):
    require_admin(user)
    if not db.query(Supermarkets).filter(Supermarkets.id == request.supermarket_id).first():
        raise HTTPException(status_code=404, detail="Supermarket not found")
    product = Products(**request.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return serialize_product(product)


@router.put("/products/{product_id}")
def admin_update_product(user: user_dependency, db: db_dependency, request: AdminProductPatch, product_id: int = Path(gt=0)):
    require_admin(user)
    product = db.query(Products).filter(Products.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    data = request.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return serialize_product(product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_product(user: user_dependency, db: db_dependency, product_id: int = Path(gt=0)):
    require_admin(user)
    product = db.query(Products).filter(Products.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.query(Cart).filter(Cart.product_id == product_id).delete(synchronize_session=False)
    db.query(Favorites).filter(Favorites.product_id == product_id).delete(synchronize_session=False)
    db.query(RecipeItems).filter(RecipeItems.product_id == product_id).delete(synchronize_session=False)
    db.query(ShoppingHistoryItem).filter(ShoppingHistoryItem.product_id == product_id).update({ShoppingHistoryItem.product_id: None}, synchronize_session=False)
    db.delete(product)
    db.commit()


@router.get("/supermarkets")
def admin_list_supermarkets(user: user_dependency, db: db_dependency):
    require_admin(user)
    return [serialize_supermarket(sm) for sm in db.query(Supermarkets).order_by(Supermarkets.name.asc()).all()]


@router.post("/supermarkets", status_code=status.HTTP_201_CREATED)
def admin_create_supermarket(user: user_dependency, db: db_dependency, request: AdminSupermarketIn):
    require_admin(user)
    sm = Supermarkets(**request.model_dump())
    db.add(sm)
    db.commit()
    db.refresh(sm)
    return serialize_supermarket(sm)


@router.put("/supermarkets/{supermarket_id}")
def admin_update_supermarket(user: user_dependency, db: db_dependency, request: AdminSupermarketIn, supermarket_id: int = Path(gt=0)):
    require_admin(user)
    sm = db.query(Supermarkets).filter(Supermarkets.id == supermarket_id).first()
    if not sm:
        raise HTTPException(status_code=404, detail="Supermarket not found")
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(sm, key, value)
    db.commit()
    db.refresh(sm)
    return serialize_supermarket(sm)


@router.delete("/supermarkets/{supermarket_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_supermarket(user: user_dependency, db: db_dependency, supermarket_id: int = Path(gt=0), force: bool = Query(default=False)):
    require_admin(user)
    sm = db.query(Supermarkets).filter(Supermarkets.id == supermarket_id).first()
    if not sm:
        raise HTTPException(status_code=404, detail="Supermarket not found")
    products_count = db.query(Products).filter(Products.supermarket_id == supermarket_id).count()
    if products_count and not force:
        raise HTTPException(status_code=400, detail=f"Supermarket has {products_count} products. Use force=true or delete/move products first.")
    if force:
        for product in db.query(Products).filter(Products.supermarket_id == supermarket_id).all():
            admin_delete_product(user, db, product.id)
    db.delete(sm)
    db.commit()


@router.get("/users")
def admin_list_users(user: user_dependency, db: db_dependency, search: Optional[str] = Query(default=None), limit: int = Query(default=100, le=500)):
    require_admin(user)
    query = db.query(Users)
    if search:
        query = query.filter(or_(Users.username.ilike(f"%{search}%"), Users.email.ilike(f"%{search}%")))
    return [serialize_user(u) for u in query.order_by(Users.id.desc()).limit(limit).all()]


@router.put("/users/{user_id}")
def admin_update_user(user: user_dependency, db: db_dependency, request: AdminUserPatch, user_id: int = Path(gt=0)):
    require_admin(user)
    target = db.query(Users).filter(Users.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(target, key, value)
    db.commit()
    db.refresh(target)
    return serialize_user(target)


@router.get("/recipes")
def admin_list_recipes(user: user_dependency, db: db_dependency, search: Optional[str] = Query(default=None), limit: int = Query(default=100, le=500)):
    require_admin(user)
    query = db.query(Recipes)
    if search:
        query = query.filter(Recipes.name.ilike(f"%{search}%"))
    return [serialize_recipe(db, r) for r in query.order_by(Recipes.id.desc()).limit(limit).all()]


@router.post("/recipes", status_code=status.HTTP_201_CREATED)
def admin_create_recipe(user: user_dependency, db: db_dependency, request: AdminRecipeIn):
    require_admin(user)
    if not db.query(Users).filter(Users.id == request.owner_id).first():
        raise HTTPException(status_code=404, detail="Owner user not found")
    recipe = Recipes(name=request.name, image=request.image, owner_id=request.owner_id)
    for field in ["description", "servings", "prep_time_minutes", "instructions"]:
        if hasattr(recipe, field):
            setattr(recipe, field, getattr(request, field))
    if hasattr(recipe, "source_type"):
        recipe.source_type = "admin"
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return serialize_recipe(db, recipe)


@router.put("/recipes/{recipe_id}")
def admin_update_recipe(user: user_dependency, db: db_dependency, request: AdminRecipePatch, recipe_id: int = Path(gt=0)):
    require_admin(user)
    recipe = db.query(Recipes).filter(Recipes.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    data = request.model_dump(exclude_unset=True)
    if data.get("owner_id") and not db.query(Users).filter(Users.id == data["owner_id"]).first():
        raise HTTPException(status_code=404, detail="Owner user not found")
    for key, value in data.items():
        if hasattr(recipe, key):
            setattr(recipe, key, value)
    db.commit()
    db.refresh(recipe)
    return serialize_recipe(db, recipe)


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_recipe(user: user_dependency, db: db_dependency, recipe_id: int = Path(gt=0)):
    require_admin(user)
    recipe = db.query(Recipes).filter(Recipes.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    db.query(RecipeItems).filter(RecipeItems.recipe_id == recipe_id).delete(synchronize_session=False)
    db.delete(recipe)
    db.commit()
