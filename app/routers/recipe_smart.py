from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy import or_, text
from sqlalchemy.orm import Session
from starlette import status

from app.database import SessionLocal, engine
from app.models import Cart, Products, RecipeItems, Recipes, Supermarkets
from app.routers.auth import get_current_user
from app.services.schema_compat import ensure_schema_compat

router = APIRouter(prefix="/smart-recipes", tags=["smart-recipes"])

_schema_checked = False


def ensure_schema_ready() -> None:
    global _schema_checked
    if not _schema_checked:
        ensure_schema_compat(engine)
        ensure_recipe_nutrition_schema()
        _schema_checked = True



NUTRITION_FIELDS = [
    "calories_kcal",
    "protein_g",
    "fat_total_g",
    "saturated_fat_g",
    "monounsaturated_fat_g",
    "polyunsaturated_fat_g",
    "carbohydrates_g",
    "sugars_g",
    "fiber_g",
    "sodium_mg",
    "calcium_mg",
    "iron_mg",
    "vitamin_d_mcg",
    "vitamin_c_mg",
]


def ensure_recipe_nutrition_schema() -> None:
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS recipe_nutrition (
                    id SERIAL PRIMARY KEY,
                    recipe_id INTEGER NOT NULL UNIQUE REFERENCES recipes(id) ON DELETE CASCADE,
                    calories_kcal NUMERIC,
                    protein_g NUMERIC,
                    fat_total_g NUMERIC,
                    saturated_fat_g NUMERIC,
                    monounsaturated_fat_g NUMERIC,
                    polyunsaturated_fat_g NUMERIC,
                    carbohydrates_g NUMERIC,
                    sugars_g NUMERIC,
                    fiber_g NUMERIC,
                    sodium_mg NUMERIC,
                    calcium_mg NUMERIC,
                    iron_mg NUMERIC,
                    vitamin_d_mcg NUMERIC,
                    vitamin_c_mg NUMERIC,
                    note TEXT,
                    created_at VARCHAR(40),
                    updated_at VARCHAR(40)
                )
            """))
        else:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS recipe_nutrition (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipe_id INTEGER NOT NULL UNIQUE,
                    calories_kcal NUMERIC,
                    protein_g NUMERIC,
                    fat_total_g NUMERIC,
                    saturated_fat_g NUMERIC,
                    monounsaturated_fat_g NUMERIC,
                    polyunsaturated_fat_g NUMERIC,
                    carbohydrates_g NUMERIC,
                    sugars_g NUMERIC,
                    fiber_g NUMERIC,
                    sodium_mg NUMERIC,
                    calcium_mg NUMERIC,
                    iron_mg NUMERIC,
                    vitamin_d_mcg NUMERIC,
                    vitamin_c_mg NUMERIC,
                    note TEXT,
                    created_at VARCHAR(40),
                    updated_at VARCHAR(40)
                )
            """))


def _nutrition_payload(value: RecipeNutritionIn | None) -> dict | None:
    if value is None:
        return None
    data = value.dict() if hasattr(value, "dict") else dict(value)
    cleaned = {}
    for key in NUTRITION_FIELDS:
        raw = data.get(key)
        cleaned[key] = None if raw in ("", None) else float(raw)
    note = (data.get("note") or "").strip()
    cleaned["note"] = note or None
    if not any(cleaned.get(key) is not None for key in NUTRITION_FIELDS) and not cleaned.get("note"):
        return None
    return cleaned


def serialize_nutrition(db: Session, recipe_id: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT calories_kcal, protein_g, fat_total_g, saturated_fat_g,
                   monounsaturated_fat_g, polyunsaturated_fat_g, carbohydrates_g,
                   sugars_g, fiber_g, sodium_mg, calcium_mg, iron_mg,
                   vitamin_d_mcg, vitamin_c_mg, note
            FROM recipe_nutrition
            WHERE recipe_id = :recipe_id
        """),
        {"recipe_id": recipe_id},
    ).first()
    if row is None:
        return None
    data = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    for key in NUTRITION_FIELDS:
        data[key] = None if data.get(key) is None else float(data[key])
    return data


def upsert_nutrition(db: Session, recipe_id: int, nutrition: RecipeNutritionIn | None) -> None:
    data = _nutrition_payload(nutrition)
    db.execute(text("DELETE FROM recipe_nutrition WHERE recipe_id = :recipe_id"), {"recipe_id": recipe_id})
    if data is None:
        return
    now = datetime.utcnow().isoformat(timespec="seconds")
    values = {"recipe_id": recipe_id, **data, "created_at": now, "updated_at": now}
    db.execute(
        text("""
            INSERT INTO recipe_nutrition (
                recipe_id, calories_kcal, protein_g, fat_total_g, saturated_fat_g,
                monounsaturated_fat_g, polyunsaturated_fat_g, carbohydrates_g,
                sugars_g, fiber_g, sodium_mg, calcium_mg, iron_mg,
                vitamin_d_mcg, vitamin_c_mg, note, created_at, updated_at
            )
            VALUES (
                :recipe_id, :calories_kcal, :protein_g, :fat_total_g, :saturated_fat_g,
                :monounsaturated_fat_g, :polyunsaturated_fat_g, :carbohydrates_g,
                :sugars_g, :fiber_g, :sodium_mg, :calcium_mg, :iron_mg,
                :vitamin_d_mcg, :vitamin_c_mg, :note, :created_at, :updated_at
            )
        """),
        values,
    )


def get_db():
    ensure_schema_ready()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class RecipeIngredientIn(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, gt=0)
    cart_quantity: int = Field(default=1, gt=0)
    amount: Optional[float] = Field(default=None, gt=0)
    amount_unit: Optional[str] = Field(default=None, max_length=40)
    note: Optional[str] = None
    is_optional: bool = False


class RecipeNutritionIn(BaseModel):
    calories_kcal: Optional[float] = Field(default=None, ge=0)
    protein_g: Optional[float] = Field(default=None, ge=0)
    fat_total_g: Optional[float] = Field(default=None, ge=0)
    saturated_fat_g: Optional[float] = Field(default=None, ge=0)
    monounsaturated_fat_g: Optional[float] = Field(default=None, ge=0)
    polyunsaturated_fat_g: Optional[float] = Field(default=None, ge=0)
    carbohydrates_g: Optional[float] = Field(default=None, ge=0)
    sugars_g: Optional[float] = Field(default=None, ge=0)
    fiber_g: Optional[float] = Field(default=None, ge=0)
    sodium_mg: Optional[float] = Field(default=None, ge=0)
    calcium_mg: Optional[float] = Field(default=None, ge=0)
    iron_mg: Optional[float] = Field(default=None, ge=0)
    vitamin_d_mcg: Optional[float] = Field(default=None, ge=0)
    vitamin_c_mg: Optional[float] = Field(default=None, ge=0)
    note: Optional[str] = Field(default=None, max_length=500)


class RecipeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    description: Optional[str] = None
    image: Optional[str] = None
    servings: int = Field(default=1, gt=0, le=50)
    prep_time_minutes: Optional[int] = Field(default=None, ge=0, le=600)
    instructions: Optional[str] = None
    items: list[RecipeIngredientIn] = Field(default_factory=list)
    nutrition: Optional[RecipeNutritionIn] = None


class RecipeUpdate(RecipeCreate):
    pass


class RestoreIngredientSelection(BaseModel):
    recipe_item_id: int = Field(gt=0)
    quantity: int = Field(default=1, gt=0)
    excluded: bool = False


class AddRecipeToCartRequest(BaseModel):
    items: Optional[list[RestoreIngredientSelection]] = None
    replace_cart: bool = False


ITALIAN_DAILY_RECIPES = [
    {
        "name": "Pasta al pomodoro e ricotta",
        "image": "",
        "description": "Ricetta italiana semplice, economica e veloce. La ricetta del giorno è generata localmente, senza siti esterni.",
        "instructions": "Cuoci la pasta, scalda il pomodoro, aggiungi ricotta o formaggio a fine cottura e condisci con olio.",
        "servings": 2,
        "ingredients": [
            {"name": "pasta", "measure": "200 g"},
            {"name": "pomodoro", "measure": "200 g"},
            {"name": "ricotta", "measure": "150 g"},
            {"name": "olio", "measure": "q.b."},
        ],
    },
    {
        "name": "Insalata di pollo estiva",
        "image": "",
        "description": "Piatto freddo utile per preparare una spesa leggera con prodotti da banco e verdure.",
        "instructions": "Cuoci il pollo, taglialo a strisce e uniscilo a insalata, carote e pomodori. Condisci a piacere.",
        "servings": 2,
        "ingredients": [
            {"name": "pollo", "measure": "350 g"},
            {"name": "insalata", "measure": "1 busta"},
            {"name": "carote", "measure": "2"},
            {"name": "pomodori", "measure": "200 g"},
        ],
    },
    {
        "name": "Cous cous con verdure",
        "image": "",
        "description": "Ricetta pratica per usare verdure in offerta e creare una lista della spesa veloce.",
        "instructions": "Prepara il cous cous, salta zucchine, melanzane e pomodori, poi mescola tutto con olio e spezie.",
        "servings": 2,
        "ingredients": [
            {"name": "cous cous", "measure": "200 g"},
            {"name": "zucchine", "measure": "250 g"},
            {"name": "melanzane", "measure": "250 g"},
            {"name": "pomodori", "measure": "200 g"},
        ],
    },
    {
        "name": "Riso con tonno e carote",
        "image": "",
        "description": "Ricetta semplice da schiscetta, con ingredienti facili da trovare nel catalogo.",
        "instructions": "Cuoci il riso, scolalo e aggiungi tonno, carote tagliate fini e olio.",
        "servings": 2,
        "ingredients": [
            {"name": "riso", "measure": "200 g"},
            {"name": "tonno", "measure": "160 g"},
            {"name": "carote", "measure": "2"},
            {"name": "olio", "measure": "q.b."},
        ],
    },
    {
        "name": "Toast tacchino e formaggio",
        "image": "",
        "description": "Ricetta rapida per creare subito una lista colazione/pranzo con prodotti reali del catalogo.",
        "instructions": "Componi il toast con pane, fesa di tacchino e formaggio. Scalda in padella o tostiera.",
        "servings": 2,
        "ingredients": [
            {"name": "pane", "measure": "4 fette"},
            {"name": "tacchino", "measure": "150 g"},
            {"name": "formaggio", "measure": "100 g"},
        ],
    },
    {
        "name": "Uova con patate e insalata",
        "image": "",
        "description": "Ricetta economica e completa basata su prodotti comuni del supermercato.",
        "instructions": "Cuoci le patate, prepara le uova e servi con insalata o verdure fresche.",
        "servings": 2,
        "ingredients": [
            {"name": "uova", "measure": "4"},
            {"name": "patate", "measure": "500 g"},
            {"name": "insalata", "measure": "1 busta"},
        ],
    },
]

INGREDIENT_ALIASES = {
    "pomodoro": ["pomodoro", "pomodori", "passata", "salsa pomodoro"],
    "pomodori": ["pomodoro", "pomodori", "datterino", "cuori di bue"],
    "pollo": ["pollo", "sovracosce", "fusi", "burger di pollo"],
    "tacchino": ["tacchino", "fesa di tacchino", "hamburger di tacchino"],
    "formaggio": ["formaggio", "caciotta", "provolone", "tomino", "mozzarella"],
    "pane": ["pane", "pan bauletto", "toast"],
    "insalata": ["insalata", "valeriana", "iceberg"],
    "olio": ["olio", "extra vergine", "olio evo"],
    "tonno": ["tonno", "rio mare"],
    "pasta": ["pasta", "fregola", "culurgiones"],
    "cous cous": ["cous cous", "couscous"],
    "riso": ["riso", "arancini"],
    "uova": ["uova", "uovo"],
    "patate": ["patate", "potatoes"],
    "carote": ["carote", "carota"],
    "zucchine": ["zucchine", "zucchina"],
    "melanzane": ["melanzane", "melanzana"],
    "ricotta": ["ricotta"],
}


def _set_if_has(model: Any, field: str, value: Any) -> None:
    if hasattr(model, field):
        setattr(model, field, value)


def require_recipe_extended_columns() -> None:
    recipe_cols = {column.name for column in Recipes.__table__.columns}
    missing = [
        field for field in ["description", "instructions", "servings", "prep_time_minutes"]
        if field not in recipe_cols
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Backend Recipes model missing columns: "
                + ", ".join(missing)
                + ". Run python scripts\\force_recipes_fields_v21.py, deploy Render, then retry."
            ),
        )



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


def current_price(product: Products | None) -> float:
    if product is None:
        return 0.0
    original = float(product.original_price or 0)
    discounted = product.discounted_price
    if discounted is not None and float(discounted) < original and _offer_is_active(product):
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


def normalize_tokens(text: str) -> set[str]:
    text = re.sub(r"[^a-zA-ZÀ-ÿ0-9]+", " ", str(text or "").lower())
    return {t for t in text.split() if len(t) >= 3}


def cheaper_alternatives(db: Session, product: Products | None, limit: int = 3) -> list[dict]:
    if not product:
        return []
    tokens = list(normalize_tokens(product.name))[:4]
    if not tokens:
        return []
    query = db.query(Products).filter(Products.id != product.id)
    query = query.filter(or_(*[Products.name.ilike(f"%{token}%") for token in tokens]))
    candidates = query.limit(40).all()
    current = current_price(product)
    cheaper = []
    for candidate in candidates:
        price = current_price(candidate)
        if price > 0 and price < current:
            cheaper.append({"product": serialize_product_min(db, candidate), "saving": round(current - price, 2)})
    cheaper.sort(key=lambda x: x["saving"], reverse=True)
    return cheaper[:limit]


def serialize_recipe_item(db: Session, item: RecipeItems) -> dict:
    product = db.query(Products).filter(Products.id == item.product_id).first()
    price = current_price(product)
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
    total = sum(float(item["line_total"] or 0) for item in serialized_items)
    servings = max(int(getattr(recipe, "servings", None) or 1), 1)
    return {
        "id": recipe.id,
        "name": recipe.name,
        "image": recipe.image,
        "owner_id": recipe.owner_id,
        "description": getattr(recipe, "description", None),
        "servings": servings,
        "prep_time_minutes": getattr(recipe, "prep_time_minutes", None),
        "instructions": getattr(recipe, "instructions", None),
        "source_type": getattr(recipe, "source_type", None) or "personal",
        "source_url": getattr(recipe, "source_url", None),
        "created_at": getattr(recipe, "created_at", None),
        "items_count": len(items),
        "estimated_total": round(total, 2),
        "estimated_per_serving": round(total / servings, 2),
        "nutrition": serialize_nutrition(db, recipe.id),
        "nutrition_basis": "per_person",
        "items": serialized_items,
    }


def ensure_owned_recipe(db: Session, recipe_id: int, owner_id: int) -> Recipes:
    recipe = db.query(Recipes).filter(Recipes.id == recipe_id).filter(Recipes.owner_id == owner_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ricetta non trovata")
    return recipe


def create_or_update_items(db: Session, recipe: Recipes, items: list[RecipeIngredientIn], replace: bool = True) -> None:
    if replace:
        db.query(RecipeItems).filter(RecipeItems.recipe_id == recipe.id).delete(synchronize_session=False)
        db.flush()
    for data in items:
        product = db.query(Products).filter(Products.id == data.product_id).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prodotto non trovato: {data.product_id}")
        item = RecipeItems(recipe_id=recipe.id, product_id=product.id, quantity=data.quantity)
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


@router.post("", status_code=status.HTTP_201_CREATED)
def create_recipe(user: user_dependency, db: db_dependency, request: RecipeCreate):
    require_recipe_extended_columns()
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
    upsert_nutrition(db, recipe.id, request.nutrition)
    db.commit()
    db.refresh(recipe)
    return serialize_recipe(db, recipe, include_items=True)


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




@router.get("/debug/model", status_code=status.HTTP_200_OK)
def debug_recipe_model(user: user_dependency):
    recipe_cols = sorted(column.name for column in Recipes.__table__.columns)
    item_cols = sorted(column.name for column in RecipeItems.__table__.columns)
    return {
        "recipes_model_columns": recipe_cols,
        "recipe_items_model_columns": item_cols,
        "has_description": "description" in recipe_cols,
        "has_instructions": "instructions" in recipe_cols,
        "has_servings": "servings" in recipe_cols,
        "has_prep_time_minutes": "prep_time_minutes" in recipe_cols,
        "has_amount": "amount" in item_cols,
        "has_cart_quantity": "cart_quantity" in item_cols,
    }


@router.get("/{recipe_id}", status_code=status.HTTP_200_OK)
def get_recipe(user: user_dependency, db: db_dependency, recipe_id: int = Path(gt=0)):
    recipe = ensure_owned_recipe(db, recipe_id, user.get("id"))
    return serialize_recipe(db, recipe, include_items=True)


@router.put("/{recipe_id}", status_code=status.HTTP_200_OK)
def update_recipe(user: user_dependency, db: db_dependency, recipe_id: int, request: RecipeUpdate):
    require_recipe_extended_columns()
    recipe = ensure_owned_recipe(db, recipe_id, user.get("id"))
    recipe.name = request.name
    recipe.image = request.image
    _set_if_has(recipe, "description", request.description)
    _set_if_has(recipe, "servings", request.servings)
    _set_if_has(recipe, "prep_time_minutes", request.prep_time_minutes)
    _set_if_has(recipe, "instructions", request.instructions)
    create_or_update_items(db, recipe, request.items, replace=True)
    upsert_nutrition(db, recipe.id, request.nutrition)
    db.commit()
    db.refresh(recipe)
    return serialize_recipe(db, recipe, include_items=True)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(user: user_dependency, db: db_dependency, recipe_id: int):
    recipe = ensure_owned_recipe(db, recipe_id, user.get("id"))
    db.execute(text("DELETE FROM recipe_nutrition WHERE recipe_id = :recipe_id"), {"recipe_id": recipe.id})
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

    added, changed_prices, skipped = [], [], []
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
            changed_prices.append({"product_id": product.id, "name": product.name, "old_price": snapshot, "current_price": now, "difference": round(now - float(snapshot), 2)})
        added.append({"product_id": product.id, "name": product.name, "quantity": qty, "current_price": now})

    db.commit()
    return {"recipe_id": recipe.id, "added_count": len(added), "added": added, "skipped_recipe_item_ids": skipped, "changed_prices": changed_prices, "message": "Ricetta aggiunta alla lista della spesa"}


def match_ingredient_to_product(db: Session, ingredient_name: str) -> Products | None:
    key = ingredient_name.lower().strip()
    terms = INGREDIENT_ALIASES.get(key, [key])
    best: list[Products] = []
    for term in terms:
        tokens = list(normalize_tokens(term))
        if not tokens:
            continue
        query = db.query(Products)
        for token in tokens[:2]:
            query = query.filter(Products.name.ilike(f"%{token}%"))
        matches = query.limit(30).all()
        best.extend(matches)
    if not best:
        # fallback: category contains term
        for term in terms:
            matches = db.query(Products).filter(Products.category.ilike(f"%{term}%")).limit(20).all()
            best.extend(matches)
    if not best:
        return None
    unique = {p.id: p for p in best}.values()
    return sorted(unique, key=lambda p: (current_price(p) <= 0, current_price(p)))[0]


def local_daily_recipe() -> dict:
    day_index = int(datetime.utcnow().strftime("%j"))
    recipe = dict(ITALIAN_DAILY_RECIPES[day_index % len(ITALIAN_DAILY_RECIPES)])
    recipe["source_type"] = "local_italian_rotation"
    recipe["source_url"] = None
    return recipe


def build_daily_response(db: Session) -> dict:
    recipe = local_daily_recipe()
    matched, missing = [], []
    total = 0.0
    for ing in recipe["ingredients"]:
        product = match_ingredient_to_product(db, ing["name"])
        if product:
            price = current_price(product)
            total += price
            matched.append({"ingredient": ing["name"], "measure": ing.get("measure"), "product": serialize_product_min(db, product), "line_total": round(price, 2)})
        else:
            missing.append(ing)
    servings = int(recipe.get("servings") or 2)
    return {
        **recipe,
        "matched_items": matched,
        "missing_ingredients": missing,
        "estimated_total": round(total, 2),
        "estimated_per_serving": round(total / max(servings, 1), 2),
        "servings": servings,
        "note": "Ricetta del giorno generata localmente: nessun sito esterno usato.",
    }
