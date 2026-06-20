from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Annotated, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette import status

from app.database import SessionLocal, engine
from app.models import Cart, Products, RecipeItems, Recipes
from app.routers.auth import get_current_user

router = APIRouter(prefix="/weekly-menus", tags=["weekly-menus"])
_schema_checked = False

MEAL_TYPES = [
    {"id": "breakfast", "label": "Colazione", "emoji": "☕"},
    {"id": "lunch", "label": "Pranzo", "emoji": "🍝"},
    {"id": "snack", "label": "Spuntino", "emoji": "🍎"},
    {"id": "dinner", "label": "Cena", "emoji": "🍽️"},
]

DAYS = [
    {"index": 0, "label": "Lunedì", "short": "Lun"},
    {"index": 1, "label": "Martedì", "short": "Mar"},
    {"index": 2, "label": "Mercoledì", "short": "Mer"},
    {"index": 3, "label": "Giovedì", "short": "Gio"},
    {"index": 4, "label": "Venerdì", "short": "Ven"},
    {"index": 5, "label": "Sabato", "short": "Sab"},
    {"index": 6, "label": "Domenica", "short": "Dom"},
]


def get_db():
    ensure_schema_ready()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class WeeklyMenuItemUpsert(BaseModel):
    week_start: date
    day_index: int = Field(ge=0, le=6)
    meal_type: Literal["breakfast", "lunch", "snack", "dinner"]
    recipe_id: int = Field(gt=0)
    servings_override: Optional[int] = Field(default=None, gt=0, le=50)
    notes: Optional[str] = Field(default=None, max_length=500)


class WeeklyMenuAddToCartRequest(BaseModel):
    replace_cart: bool = False


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _week_start(value: date | None = None) -> date:
    today = value or date.today()
    return today - timedelta(days=today.weekday())


def _dialect() -> str:
    return engine.dialect.name


def ensure_schema_ready() -> None:
    global _schema_checked
    if _schema_checked:
        return

    dialect = _dialect()
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS weekly_menus (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    week_start DATE NOT NULL,
                    title VARCHAR(160),
                    created_at VARCHAR(40),
                    updated_at VARCHAR(40)
                )
            """))
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ux_weekly_menus_user_week
                ON weekly_menus(user_id, week_start)
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS weekly_menu_items (
                    id SERIAL PRIMARY KEY,
                    weekly_menu_id INTEGER NOT NULL REFERENCES weekly_menus(id) ON DELETE CASCADE,
                    day_index INTEGER NOT NULL CHECK (day_index >= 0 AND day_index <= 6),
                    meal_type VARCHAR(30) NOT NULL,
                    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
                    servings_override INTEGER,
                    notes TEXT,
                    position INTEGER DEFAULT 0,
                    created_at VARCHAR(40),
                    updated_at VARCHAR(40)
                )
            """))
            conn.execute(text("DROP INDEX IF EXISTS ux_weekly_menu_items_slot"))
            conn.execute(text("""
                ALTER TABLE weekly_menu_items
                ADD COLUMN IF NOT EXISTS position INTEGER DEFAULT 0
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_weekly_menu_items_slot
                ON weekly_menu_items(weekly_menu_id, day_index, meal_type)
            """))
        else:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS weekly_menus (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    week_start VARCHAR(20) NOT NULL,
                    title VARCHAR(160),
                    created_at VARCHAR(40),
                    updated_at VARCHAR(40)
                )
            """))
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ux_weekly_menus_user_week
                ON weekly_menus(user_id, week_start)
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS weekly_menu_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    weekly_menu_id INTEGER NOT NULL,
                    day_index INTEGER NOT NULL,
                    meal_type VARCHAR(30) NOT NULL,
                    recipe_id INTEGER NOT NULL,
                    servings_override INTEGER,
                    notes TEXT,
                    position INTEGER DEFAULT 0,
                    created_at VARCHAR(40),
                    updated_at VARCHAR(40)
                )
            """))
            conn.execute(text("DROP INDEX IF EXISTS ux_weekly_menu_items_slot"))
            try:
                conn.execute(text("ALTER TABLE weekly_menu_items ADD COLUMN position INTEGER DEFAULT 0"))
            except Exception:
                pass
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_weekly_menu_items_slot
                ON weekly_menu_items(weekly_menu_id, day_index, meal_type)
            """))

    _schema_checked = True


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    return dict(row._mapping) if hasattr(row, "_mapping") else dict(row)


def _insert_menu(db: Session, user_id: int, week_start: date) -> int:
    now = _now_iso()
    title = f"Menu settimana {week_start.isoformat()}"
    if _dialect() == "postgresql":
        return db.execute(
            text("""
                INSERT INTO weekly_menus (user_id, week_start, title, created_at, updated_at)
                VALUES (:user_id, :week_start, :title, :created_at, :updated_at)
                RETURNING id
            """),
            {"user_id": user_id, "week_start": week_start, "title": title, "created_at": now, "updated_at": now},
        ).scalar_one()

    db.execute(
        text("""
            INSERT INTO weekly_menus (user_id, week_start, title, created_at, updated_at)
            VALUES (:user_id, :week_start, :title, :created_at, :updated_at)
        """),
        {"user_id": user_id, "week_start": week_start.isoformat(), "title": title, "created_at": now, "updated_at": now},
    )
    return db.execute(text("SELECT last_insert_rowid()")).scalar_one()


def ensure_menu(db: Session, user_id: int, week_start: date) -> dict:
    week_start = _week_start(week_start)
    row = db.execute(
        text("""
            SELECT id, user_id, week_start, title, created_at, updated_at
            FROM weekly_menus
            WHERE user_id = :user_id AND week_start = :week_start
        """),
        {"user_id": user_id, "week_start": week_start},
    ).first()

    if row is None:
        menu_id = _insert_menu(db, user_id, week_start)
        db.flush()
        row = db.execute(text("SELECT id, user_id, week_start, title, created_at, updated_at FROM weekly_menus WHERE id = :id"), {"id": menu_id}).first()

    menu = _row_to_dict(row)
    menu["week_start"] = str(menu["week_start"])[:10]
    menu["week_end"] = (week_start + timedelta(days=6)).isoformat()
    return menu


def _offer_is_active(product: Products) -> bool:
    valid_to = getattr(product, "flyer_valid_to", None)
    if not valid_to:
        return True
    try:
        return datetime.fromisoformat(str(valid_to)[:10]).date() >= date.today()
    except Exception:
        return True


def current_price(product: Products | None) -> float:
    if product is None:
        return 0.0
    original = float(product.original_price or 0)
    discounted = getattr(product, "discounted_price", None)
    if discounted is not None and original > 0 and float(discounted) < original and _offer_is_active(product):
        return float(discounted)
    return original


def serialize_product(product: Products | None) -> dict | None:
    if product is None:
        return None
    return {
        "id": product.id,
        "name": product.name,
        "image": product.image,
        "category": product.category,
        "unit": product.unit,
        "original_price": product.original_price,
        "discounted_price": getattr(product, "discounted_price", None),
        "current_price": round(current_price(product), 2),
    }


def serialize_recipe(db: Session, recipe: Recipes | None) -> dict | None:
    if recipe is None:
        return None

    items = db.query(RecipeItems).filter(RecipeItems.recipe_id == recipe.id).all()
    total = 0.0
    ingredients = []
    first_image = None

    for item in items:
        product = db.query(Products).filter(Products.id == item.product_id).first()
        qty = int(getattr(item, "cart_quantity", None) or item.quantity or 1)
        price = current_price(product)
        total += price * qty
        if product and product.image and not first_image:
            first_image = product.image
        ingredients.append({
            "id": item.id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "cart_quantity": qty,
            "amount": getattr(item, "amount", None),
            "amount_unit": getattr(item, "amount_unit", None),
            "note": getattr(item, "note", None),
            "product": serialize_product(product),
            "line_total": round(price * qty, 2),
        })

    servings = int(getattr(recipe, "servings", None) or 1)
    image = recipe.image or first_image

    return {
        "id": recipe.id,
        "name": recipe.name,
        "image": image,
        "owner_id": recipe.owner_id,
        "description": getattr(recipe, "description", None),
        "servings": servings,
        "prep_time_minutes": getattr(recipe, "prep_time_minutes", None),
        "instructions": getattr(recipe, "instructions", None),
        "items_count": len(items),
        "estimated_total": round(total, 2),
        "estimated_per_serving": round(total / max(servings, 1), 2),
        "items": ingredients,
    }


def _serialize_menu(db: Session, menu: dict) -> dict:
    rows = db.execute(
        text("""
            SELECT id, weekly_menu_id, day_index, meal_type, recipe_id, servings_override, notes, COALESCE(position, 0) AS position, created_at, updated_at
            FROM weekly_menu_items
            WHERE weekly_menu_id = :menu_id
            ORDER BY day_index ASC,
                CASE meal_type
                    WHEN 'breakfast' THEN 1
                    WHEN 'lunch' THEN 2
                    WHEN 'snack' THEN 3
                    WHEN 'dinner' THEN 4
                    ELSE 9
                END,
                COALESCE(position, 0) ASC,
                id ASC
        """),
        {"menu_id": menu["id"]},
    ).fetchall()

    items = []
    total = 0.0
    planned = 0
    for row in rows:
        item = _row_to_dict(row)
        recipe = db.query(Recipes).filter(Recipes.id == item["recipe_id"]).first()
        recipe_data = serialize_recipe(db, recipe)
        if recipe_data:
            total += float(recipe_data["estimated_total"] or 0)
            planned += 1
        item["recipe"] = recipe_data
        items.append(item)

    return {
        "menu": menu,
        "days": DAYS,
        "meal_types": MEAL_TYPES,
        "items": items,
        "summary": {
            "planned_meals": planned,
            "estimated_total": round(total, 2),
            "week_start": menu["week_start"],
            "week_end": menu["week_end"],
        },
    }


def _ensure_owned_menu(db: Session, menu_id: int, user_id: int) -> dict:
    row = db.execute(
        text("SELECT id, user_id, week_start, title, created_at, updated_at FROM weekly_menus WHERE id = :id AND user_id = :user_id"),
        {"id": menu_id, "user_id": user_id},
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu settimanale non trovato")
    menu = _row_to_dict(row)
    menu["week_start"] = str(menu["week_start"])[:10]
    menu["week_end"] = (datetime.fromisoformat(menu["week_start"]).date() + timedelta(days=6)).isoformat()
    return menu


def _ensure_owned_item(db: Session, item_id: int, user_id: int) -> dict:
    row = db.execute(
        text("""
            SELECT wmi.id, wmi.weekly_menu_id, wmi.day_index, wmi.meal_type, wmi.recipe_id
            FROM weekly_menu_items wmi
            JOIN weekly_menus wm ON wm.id = wmi.weekly_menu_id
            WHERE wmi.id = :item_id AND wm.user_id = :user_id
        """),
        {"item_id": item_id, "user_id": user_id},
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot menu non trovato")
    return _row_to_dict(row)


@router.get("", status_code=status.HTTP_200_OK)
def get_weekly_menu(user: user_dependency, db: db_dependency, week_start: Optional[date] = Query(default=None)):
    menu = ensure_menu(db, user.get("id"), _week_start(week_start))
    db.commit()
    return _serialize_menu(db, menu)


@router.get("/recipes", status_code=status.HTTP_200_OK)
def list_available_recipes(user: user_dependency, db: db_dependency):
    recipes = db.query(Recipes).filter(Recipes.owner_id == user.get("id")).order_by(Recipes.id.desc()).all()
    return [serialize_recipe(db, recipe) for recipe in recipes]


@router.post("/item", status_code=status.HTTP_200_OK)
def add_weekly_menu_item(user: user_dependency, db: db_dependency, request: WeeklyMenuItemUpsert):
    owner_id = user.get("id")
    menu = ensure_menu(db, owner_id, _week_start(request.week_start))

    recipe = db.query(Recipes).filter(Recipes.id == request.recipe_id).filter(Recipes.owner_id == owner_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ricetta non trovata")

    next_position = db.execute(
        text("""
            SELECT COALESCE(MAX(position), 0) + 1
            FROM weekly_menu_items
            WHERE weekly_menu_id = :menu_id
              AND day_index = :day_index
              AND meal_type = :meal_type
        """),
        {
            "menu_id": menu["id"],
            "day_index": request.day_index,
            "meal_type": request.meal_type,
        },
    ).scalar_one()

    now = _now_iso()
    db.execute(
        text("""
            INSERT INTO weekly_menu_items
                (weekly_menu_id, day_index, meal_type, recipe_id, servings_override, notes, position, created_at, updated_at)
            VALUES
                (:weekly_menu_id, :day_index, :meal_type, :recipe_id, :servings_override, :notes, :position, :created_at, :updated_at)
        """),
        {
            "weekly_menu_id": menu["id"],
            "day_index": request.day_index,
            "meal_type": request.meal_type,
            "recipe_id": request.recipe_id,
            "servings_override": request.servings_override,
            "notes": request.notes,
            "position": next_position,
            "created_at": now,
            "updated_at": now,
        },
    )

    db.execute(
        text("UPDATE weekly_menus SET updated_at = :updated_at WHERE id = :id"),
        {"updated_at": now, "id": menu["id"]},
    )
    db.commit()
    menu = ensure_menu(db, owner_id, _week_start(request.week_start))
    return _serialize_menu(db, menu)


@router.delete("/item/{item_id}", status_code=status.HTTP_200_OK)
def delete_weekly_menu_item(user: user_dependency, db: db_dependency, item_id: int = Path(gt=0)):
    owner_id = user.get("id")
    item = _ensure_owned_item(db, item_id, owner_id)
    menu = _ensure_owned_menu(db, item["weekly_menu_id"], owner_id)
    db.execute(text("DELETE FROM weekly_menu_items WHERE id = :id"), {"id": item_id})
    db.execute(text("UPDATE weekly_menus SET updated_at = :updated_at WHERE id = :id"), {"updated_at": _now_iso(), "id": menu["id"]})
    db.commit()
    return _serialize_menu(db, menu)


@router.post("/{menu_id}/add-to-cart", status_code=status.HTTP_201_CREATED)
def add_weekly_menu_to_cart(user: user_dependency, db: db_dependency, request: WeeklyMenuAddToCartRequest, menu_id: int = Path(gt=0)):
    owner_id = user.get("id")
    _ensure_owned_menu(db, menu_id, owner_id)

    if request.replace_cart:
        db.query(Cart).filter(Cart.owner_id == owner_id).delete(synchronize_session=False)
        db.flush()

    rows = db.execute(text("SELECT recipe_id FROM weekly_menu_items WHERE weekly_menu_id = :menu_id"), {"menu_id": menu_id}).fetchall()
    aggregated: dict[int, int] = {}
    for row in rows:
        for item in db.query(RecipeItems).filter(RecipeItems.recipe_id == row[0]).all():
            qty = int(getattr(item, "cart_quantity", None) or item.quantity or 1)
            aggregated[item.product_id] = aggregated.get(item.product_id, 0) + qty

    added = []
    for product_id, qty in aggregated.items():
        product = db.query(Products).filter(Products.id == product_id).first()
        if not product:
            continue
        existing = db.query(Cart).filter(Cart.owner_id == owner_id).filter(Cart.product_id == product_id).first()
        if existing:
            existing.quantity += qty
            existing.checked = False
        else:
            db.add(Cart(product_id=product_id, quantity=qty, owner_id=owner_id, checked=False))
        added.append({"product_id": product_id, "name": product.name, "quantity": qty, "current_price": current_price(product)})

    db.commit()
    return {"menu_id": menu_id, "added_count": len(added), "added": added, "message": "Ingredienti del menu settimanale aggiunti alla lista della spesa"}


@router.post("/{menu_id}/duplicate-next-week", status_code=status.HTTP_200_OK)
def duplicate_menu_next_week(user: user_dependency, db: db_dependency, menu_id: int = Path(gt=0)):
    owner_id = user.get("id")
    menu = _ensure_owned_menu(db, menu_id, owner_id)
    current_week = datetime.fromisoformat(str(menu["week_start"])[:10]).date()
    next_menu = ensure_menu(db, owner_id, current_week + timedelta(days=7))

    db.execute(text("DELETE FROM weekly_menu_items WHERE weekly_menu_id = :menu_id"), {"menu_id": next_menu["id"]})
    rows = db.execute(text("SELECT day_index, meal_type, recipe_id, servings_override, notes FROM weekly_menu_items WHERE weekly_menu_id = :menu_id"), {"menu_id": menu_id}).fetchall()

    now = _now_iso()
    for row in rows:
        data = _row_to_dict(row)
        db.execute(
            text("""
                INSERT INTO weekly_menu_items
                    (weekly_menu_id, day_index, meal_type, recipe_id, servings_override, notes, position, created_at, updated_at)
                VALUES
                    (:weekly_menu_id, :day_index, :meal_type, :recipe_id, :servings_override, :notes, :position, :created_at, :updated_at)
            """),
            {
                "weekly_menu_id": next_menu["id"],
                "day_index": data["day_index"],
                "meal_type": data["meal_type"],
                "recipe_id": data["recipe_id"],
                "servings_override": data["servings_override"],
                "notes": data["notes"],
                "position": data.get("position") or 0,
                "created_at": now,
                "updated_at": now,
            },
        )

    db.commit()
    return _serialize_menu(db, next_menu)


@router.get("/{menu_id}", status_code=status.HTTP_200_OK)
def get_weekly_menu_by_id(user: user_dependency, db: db_dependency, menu_id: int = Path(gt=0)):
    menu = _ensure_owned_menu(db, menu_id, user.get("id"))
    return _serialize_menu(db, menu)
