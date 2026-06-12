from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from starlette import status

from app.database import SessionLocal
from app.models import Cart, Products, RecipeItems, Recipes, Supermarkets
from app.routers.auth import get_current_user

router = APIRouter(prefix="/smart-recipes", tags=["smart-recipes"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class RecipeIngredientIn(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, gt=0, description="How many catalog units to add to cart")
    cart_quantity: int = Field(default=1, gt=0)
    amount: Optional[float] = Field(default=None, gt=0)
    amount_unit: Optional[str] = Field(default=None, max_length=40)
    note: Optional[str] = None
    is_optional: bool = False


class RecipeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    description: Optional[str] = None
    image: Optional[str] = None
    servings: int = Field(default=1, gt=0, le=50)
    prep_time_minutes: Optional[int] = Field(default=None, ge=0, le=600)
    instructions: Optional[str] = None
    items: list[RecipeIngredientIn] = Field(default_factory=list)


class RecipeUpdate(RecipeCreate):
    pass


class RestoreIngredientSelection(BaseModel):
    recipe_item_id: int = Field(gt=0)
    quantity: int = Field(default=1, gt=0)
    excluded: bool = False


class AddRecipeToCartRequest(BaseModel):
    items: Optional[list[RestoreIngredientSelection]] = None
    replace_cart: bool = False


ITALIAN_INGREDIENT_ALIASES = {
    "egg": "uova", "eggs": "uova", "milk": "latte", "butter": "burro", "flour": "farina",
    "sugar": "zucchero", "salt": "sale", "pepper": "pepe", "olive oil": "olio",
    "oil": "olio", "tomato": "pomodoro", "tomatoes": "pomodori", "chicken": "pollo",
    "beef": "manzo", "pork": "suino", "rice": "riso", "pasta": "pasta", "onion": "cipolla",
    "garlic": "aglio", "cheese": "formaggio", "parmesan": "parmigiano", "mozzarella": "mozzarella",
    "potato": "patate", "potatoes": "patate", "carrot": "carote", "carrots": "carote",
    "zucchini": "zucchine", "aubergine": "melanzane", "eggplant": "melanzane", "lemon": "limone",
    "cream": "panna", "yogurt": "yogurt", "tuna": "tonno", "salmon": "salmone",
}


DAILY_SEARCH_NAMES = [
    "Arrabiata", "Carbonara", "Chicken", "Risotto", "Pasta", "Salmon", "Beef", "Vegetarian", "Soup", "Pizza",
]


def _set_if_has(model: Any, field: str, value: Any) -> None:
    if hasattr(model, field):
        setattr(model, field, value)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")[:10])
    except ValueError:
        return None


def _offer_is_active(product: Products) -> bool:
    valid_to = getattr(product, "flyer_valid_to", None)
    end = _parse_date(valid_to)
    if end is None:
        return True
    return end.date() >= datetime.utcnow().date()


def current_price(product: Products) -> float:
    original = float(product.original_price or 0)
    discounted = product.discounted_price
    if discounted is not None and discounted < original and _offer_is_active(product):
        return float(discounted)
    return original


def _supermarket_name(db: Session, product: Products) -> str | None:
    if getattr(product, "supermarket", None):
        return product.supermarket.name
    sm = db.query(Supermarkets).filter(Supermarkets.id == product.supermarket_id).first()
    return sm.name if sm else None


def serialize_product_min(db: Session, product: Products | None) -> dict | None:
    if not product:
        return None
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "unit": product.unit,
        "image": product.image,
        "supermarket_id": product.supermarket_id,
        "supermarket_name": _supermarket_name(db, product),
        "original_price": product.original_price,
        "discounted_price": product.discounted_price if _offer_is_active(product) else None,
        "current_price": current_price(product),
        "flyer_page": getattr(product, "flyer_page", None),
        "is_lidl_plus": bool(getattr(product, "is_lidl_plus", False)),
    }


def serialize_recipe_item(db: Session, item: RecipeItems) -> dict:
    product = db.query(Products).filter(Products.id == item.product_id).first()
    price = current_price(product) if product else 0
    cart_qty = int(getattr(item, "cart_quantity", None) or item.quantity or 1)
    snapshot_price = getattr(item, "snapshot_price", None)
    return {
        "id": item.id,
        "recipe_id": item.recipe_id,
        "product_id": item.product_id,
        "quantity": item.quantity,
        "cart_quantity": cart_qty,
        "amount": getattr(item, "amount", None),
        "amount_unit": getattr(item, "amount_unit", None),
        "note": getattr(item, "note", None),
        "is_optional": bool(getattr(item, "is_optional", False)),
        "snapshot_price": snapshot_price,
        "price_changed": snapshot_price is not None and round(float(snapshot_price), 2) != round(float(price), 2),
        "line_total": round(price * cart_qty, 2),
        "product": serialize_product_min(db, product),
        "cheaper_alternatives": cheaper_alternatives(db, product, limit=3) if product else [],
    }


def serialize_recipe(db: Session, recipe: Recipes, include_items: bool = True) -> dict:
    items = db.query(RecipeItems).filter(RecipeItems.recipe_id == recipe.id).all()
    serialized_items = [serialize_recipe_item(db, item) for item in items] if include_items else []
    total = sum(item["line_total"] for item in serialized_items)
    return {
        "id": recipe.id,
        "name": recipe.name,
        "image": recipe.image,
        "owner_id": recipe.owner_id,
        "description": getattr(recipe, "description", None),
        "servings": getattr(recipe, "servings", None) or 1,
        "prep_time_minutes": getattr(recipe, "prep_time_minutes", None),
        "instructions": getattr(recipe, "instructions", None),
        "source_type": getattr(recipe, "source_type", None) or "personal",
        "source_url": getattr(recipe, "source_url", None),
        "created_at": getattr(recipe, "created_at", None),
        "items_count": len(items),
        "estimated_total": round(total, 2),
        "estimated_per_serving": round(total / max(int(getattr(recipe, "servings", None) or 1), 1), 2),
        "items": serialized_items,
    }


def normalize_tokens(text: str) -> set[str]:
    text = re.sub(r"[^a-zA-ZÀ-ÿ0-9]+", " ", text.lower())
    tokens = {t for t in text.split() if len(t) >= 3}
    return tokens


def cheaper_alternatives(db: Session, product: Products | None, limit: int = 3) -> list[dict]:
    if not product:
        return []
    tokens = list(normalize_tokens(product.name))[:4]
    if not tokens:
        return []
    query = db.query(Products).filter(Products.id != product.id)
    clauses = [Products.name.ilike(f"%{token}%") for token in tokens]
    query = query.filter(or_(*clauses))
    candidates = query.limit(40).all()
    current = current_price(product)
    cheaper = []
    for candidate in candidates:
        price = current_price(candidate)
        if price > 0 and price < current:
            cheaper.append({
                "product": serialize_product_min(db, candidate),
                "saving": round(current - price, 2),
            })
    cheaper.sort(key=lambda x: x["saving"], reverse=True)
    return cheaper[:limit]


def ensure_owned_recipe(db: Session, recipe_id: int, owner_id: int) -> Recipes:
    recipe = db.query(Recipes).filter(Recipes.id == recipe_id).filter(Recipes.owner_id == owner_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return recipe


def create_or_update_items(db: Session, recipe: Recipes, items: list[RecipeIngredientIn], replace: bool = True) -> None:
    if replace:
        db.query(RecipeItems).filter(RecipeItems.recipe_id == recipe.id).delete(synchronize_session=False)
        db.flush()
    for data in items:
        product = db.query(Products).filter(Products.id == data.product_id).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product not found: {data.product_id}")
        item = RecipeItems(
            recipe_id=recipe.id,
            product_id=product.id,
            quantity=data.quantity,
        )
        _set_if_has(item, "cart_quantity", data.cart_quantity or data.quantity or 1)
        _set_if_has(item, "amount", data.amount)
        _set_if_has(item, "amount_unit", data.amount_unit)
        _set_if_has(item, "note", data.note)
        _set_if_has(item, "is_optional", data.is_optional)
        _set_if_has(item, "snapshot_price", current_price(product))
        db.add(item)


@router.get("", status_code=status.HTTP_200_OK)
def list_recipes(user: user_dependency, db: db_dependency):
    recipes = db.query(Recipes).filter(Recipes.owner_id == user.get("id")).order_by(Recipes.id.desc()).all()
    return [serialize_recipe(db, recipe, include_items=True) for recipe in recipes]


@router.get("/{recipe_id}", status_code=status.HTTP_200_OK)
def get_recipe(user: user_dependency, db: db_dependency, recipe_id: int = Path(gt=0)):
    recipe = ensure_owned_recipe(db, recipe_id, user.get("id"))
    return serialize_recipe(db, recipe, include_items=True)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_recipe(user: user_dependency, db: db_dependency, request: RecipeCreate):
    recipe = Recipes(name=request.name, image=request.image, owner_id=user.get("id"))
    _set_if_has(recipe, "description", request.description)
    _set_if_has(recipe, "servings", request.servings)
    _set_if_has(recipe, "prep_time_minutes", request.prep_time_minutes)
    _set_if_has(recipe, "instructions", request.instructions)
    _set_if_has(recipe, "source_type", "personal")
    _set_if_has(recipe, "created_at", datetime.utcnow().isoformat(timespec="seconds"))
    db.add(recipe)
    db.flush()
    create_or_update_items(db, recipe, request.items, replace=False)
    db.commit()
    db.refresh(recipe)
    return serialize_recipe(db, recipe, include_items=True)


@router.put("/{recipe_id}", status_code=status.HTTP_200_OK)
def update_recipe(user: user_dependency, db: db_dependency, recipe_id: int, request: RecipeUpdate):
    recipe = ensure_owned_recipe(db, recipe_id, user.get("id"))
    recipe.name = request.name
    recipe.image = request.image
    _set_if_has(recipe, "description", request.description)
    _set_if_has(recipe, "servings", request.servings)
    _set_if_has(recipe, "prep_time_minutes", request.prep_time_minutes)
    _set_if_has(recipe, "instructions", request.instructions)
    create_or_update_items(db, recipe, request.items, replace=True)
    db.commit()
    db.refresh(recipe)
    return serialize_recipe(db, recipe, include_items=True)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(user: user_dependency, db: db_dependency, recipe_id: int):
    recipe = ensure_owned_recipe(db, recipe_id, user.get("id"))
    db.query(RecipeItems).filter(RecipeItems.recipe_id == recipe.id).delete(synchronize_session=False)
    db.delete(recipe)
    db.commit()


@router.get("/{recipe_id}/shopping-preview", status_code=status.HTTP_200_OK)
def recipe_shopping_preview(user: user_dependency, db: db_dependency, recipe_id: int = Path(gt=0)):
    recipe = ensure_owned_recipe(db, recipe_id, user.get("id"))
    return serialize_recipe(db, recipe, include_items=True)


@router.post("/{recipe_id}/add-to-cart", status_code=status.HTTP_201_CREATED)
def add_recipe_to_cart(user: user_dependency, db: db_dependency, recipe_id: int, request: AddRecipeToCartRequest | None = None):
    owner_id = user.get("id")
    recipe = ensure_owned_recipe(db, recipe_id, owner_id)
    items = db.query(RecipeItems).filter(RecipeItems.recipe_id == recipe.id).all()
    request = request or AddRecipeToCartRequest()

    if request.replace_cart:
        db.query(Cart).filter(Cart.owner_id == owner_id).delete(synchronize_session=False)
        db.flush()

    selected_map = None
    if request.items is not None:
        selected_map = {sel.recipe_item_id: sel for sel in request.items if not sel.excluded}

    added = []
    changed_prices = []
    skipped = []

    for item in items:
        if selected_map is not None and item.id not in selected_map:
            skipped.append(item.id)
            continue
        product = db.query(Products).filter(Products.id == item.product_id).first()
        if not product:
            skipped.append(item.id)
            continue
        selected = selected_map.get(item.id) if selected_map else None
        qty = selected.quantity if selected else int(getattr(item, "cart_quantity", None) or item.quantity or 1)
        existing = db.query(Cart).filter(Cart.owner_id == owner_id).filter(Cart.product_id == product.id).first()
        if existing:
            existing.quantity += qty
            existing.checked = False
        else:
            db.add(Cart(product_id=product.id, quantity=qty, owner_id=owner_id, checked=False))
        snapshot = getattr(item, "snapshot_price", None)
        now = current_price(product)
        if snapshot is not None and round(float(snapshot), 2) != round(float(now), 2):
            changed_prices.append({
                "product_id": product.id,
                "name": product.name,
                "old_price": snapshot,
                "current_price": now,
                "difference": round(now - float(snapshot), 2),
            })
        added.append({"product_id": product.id, "name": product.name, "quantity": qty, "current_price": now})

    db.commit()
    return {
        "recipe_id": recipe.id,
        "added_count": len(added),
        "added": added,
        "skipped_recipe_item_ids": skipped,
        "changed_prices": changed_prices,
        "message": "Ricetta aggiunta alla lista della spesa",
    }


def _fetch_mealdb_daily() -> dict | None:
    day_index = int(datetime.utcnow().strftime("%j"))
    query = DAILY_SEARCH_NAMES[day_index % len(DAILY_SEARCH_NAMES)]
    url = "https://www.themealdb.com/api/json/v1/1/search.php?s=" + urllib.parse.quote(query)
    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
        meals = payload.get("meals") or []
        if not meals:
            return None
        meal = meals[day_index % len(meals)]
        ingredients = []
        for i in range(1, 21):
            ingredient = (meal.get(f"strIngredient{i}") or "").strip()
            measure = (meal.get(f"strMeasure{i}") or "").strip()
            if ingredient:
                ingredients.append({"name": ingredient, "measure": measure})
        return {
            "name": meal.get("strMeal"),
            "image": meal.get("strMealThumb"),
            "description": meal.get("strCategory") or meal.get("strArea") or "Ricetta del giorno",
            "instructions": meal.get("strInstructions"),
            "source_url": meal.get("strSource") or meal.get("strYoutube") or "https://www.themealdb.com/",
            "ingredients": ingredients,
            "source_type": "internet_themealdb",
        }
    except Exception:
        return None


def _fallback_daily() -> dict:
    return {
        "name": "Pasta veloce con pomodoro e formaggio",
        "image": "",
        "description": "Fallback locale se la ricetta online non risponde.",
        "instructions": "Cuoci la pasta, scalda il pomodoro, aggiungi formaggio e olio a fine cottura.",
        "source_url": None,
        "source_type": "local_fallback",
        "ingredients": [
            {"name": "pasta", "measure": "200 g"},
            {"name": "tomato", "measure": "200 g"},
            {"name": "cheese", "measure": "q.b."},
            {"name": "olive oil", "measure": "q.b."},
        ],
    }


def match_ingredient_to_product(db: Session, ingredient_name: str) -> Products | None:
    name = ingredient_name.lower().strip()
    alias = ITALIAN_INGREDIENT_ALIASES.get(name, name)
    search_terms = [alias, name]
    for term in search_terms:
        tokens = list(normalize_tokens(term))
        if not tokens:
            continue
        query = db.query(Products)
        for token in tokens[:2]:
            query = query.filter(Products.name.ilike(f"%{token}%"))
        matches = query.limit(20).all()
        if matches:
            matches.sort(key=current_price)
            return matches[0]
    return None


def build_daily_response(db: Session) -> dict:
    recipe = _fetch_mealdb_daily() or _fallback_daily()
    matched = []
    missing = []
    total = 0.0
    for ing in recipe["ingredients"]:
        product = match_ingredient_to_product(db, ing["name"])
        if product:
            price = current_price(product)
            total += price
            matched.append({
                "ingredient": ing["name"],
                "measure": ing.get("measure"),
                "product": serialize_product_min(db, product),
                "line_total": round(price, 2),
            })
        else:
            missing.append(ing)
    return {
        **recipe,
        "matched_items": matched,
        "missing_ingredients": missing,
        "estimated_total": round(total, 2),
        "estimated_per_serving": round(total / 2, 2),
        "servings": 2,
    }


@router.get("/daily/today", status_code=status.HTTP_200_OK)
def daily_recipe(user: user_dependency, db: db_dependency):
    return build_daily_response(db)


@router.post("/daily/add-to-cart", status_code=status.HTTP_201_CREATED)
def add_daily_recipe_to_cart(user: user_dependency, db: db_dependency):
    daily = build_daily_response(db)
    owner_id = user.get("id")
    added = []
    for match in daily["matched_items"]:
        product_id = match["product"]["id"]
        existing = db.query(Cart).filter(Cart.owner_id == owner_id).filter(Cart.product_id == product_id).first()
        if existing:
            existing.quantity += 1
            existing.checked = False
        else:
            db.add(Cart(product_id=product_id, quantity=1, owner_id=owner_id, checked=False))
        added.append(match)
    db.commit()
    return {
        "added_count": len(added),
        "added": added,
        "missing_ingredients": daily["missing_ingredients"],
        "estimated_total": daily["estimated_total"],
    }
