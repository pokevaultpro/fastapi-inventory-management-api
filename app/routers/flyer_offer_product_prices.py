from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.routers.auth import get_current_user
from app.services.flyer_offer_schema import ensure_flyer_offer_schema


router = APIRouter(prefix="/admin/flyer-offer-prices", tags=["admin-flyer-offer-prices"])


def get_db():
    ensure_flyer_offer_schema(engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def require_admin(user: dict) -> None:
    if not user or user.get("user_role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


def product_columns(db: Session) -> set[str]:
    if engine.dialect.name == "postgresql":
        rows = db.execute(
            text("SELECT column_name AS name FROM information_schema.columns WHERE table_name='products'")
        ).mappings().all()
        return {row["name"] for row in rows}
    rows = db.execute(text("PRAGMA table_info(products)")).mappings().all()
    return {row["name"] for row in rows}


def pick_original_price(product: dict[str, Any], offer: dict[str, Any]) -> float | None:
    offer_price = float(offer["offer_price"]) if offer["offer_price"] is not None else None
    if offer_price is None:
        return None

    for key in ["original_price"]:
        value = offer.get(key)
        if value is not None:
            try:
                old = float(value)
                if old > offer_price:
                    return old
            except Exception:
                pass

    # Fallback: if the catalog product already has a normal price higher than the offer,
    # use it as the crossed/original price.
    for key in ["original_price", "discounted_price"]:
        value = product.get(key)
        if value is not None:
            try:
                old = float(value)
                if old > offer_price:
                    return old
            except Exception:
                pass

    return None


def update_product_for_offer(db: Session, cols: set[str], offer: dict[str, Any]) -> bool:
    product = db.execute(
        text("SELECT * FROM products WHERE id = :id"),
        {"id": offer["product_id"]},
    ).mappings().first()
    if not product:
        return False

    offer_price = offer.get("offer_price")
    if offer_price is None:
        return False

    original = pick_original_price(dict(product), offer)

    assignments: dict[str, Any] = {}

    if "discounted_price" in cols:
        assignments["discounted_price"] = float(offer_price)

    if "original_price" in cols and original is not None:
        assignments["original_price"] = float(original)

    # These fields were introduced by earlier flyer/catalog patches.
    mapping = {
        "flyer_page": offer.get("flyer_page"),
        "flyer_valid_from": offer.get("valid_from"),
        "flyer_valid_to": offer.get("valid_to"),
        "flyer_source": offer.get("source"),
        "flyer_source_url": offer.get("source_url"),
        "offer_note": offer.get("offer_note"),
        "price_type": offer.get("price_type"),
        "price_unit": offer.get("price_unit"),
    }
    for field, value in mapping.items():
        if field in cols and value is not None:
            assignments[field] = value

    if not assignments:
        return False

    set_sql = ", ".join(f"{field} = :{field}" for field in assignments)
    params = {"id": offer["product_id"], **assignments}
    db.execute(text(f"UPDATE products SET {set_sql} WHERE id = :id"), params)
    return True


@router.post("/apply/{flyer_id}")
def apply_flyer_prices(user: user_dependency, db: db_dependency, flyer_id: int):
    """
    Materializes approved/published flyer offers into Products fields.

    This is a compatibility layer for the existing frontend, which still reads
    Products.original_price / Products.discounted_price to decide whether to show an offer.
    The source of truth remains flyer_offers.
    """
    require_admin(user)
    cols = product_columns(db)

    if "discounted_price" not in cols:
        raise HTTPException(status_code=400, detail="Products.discounted_price column not found")

    offers = db.execute(
        text("""
            SELECT o.*
            FROM flyer_offers o
            WHERE o.flyer_id = :flyer_id
              AND o.product_id IS NOT NULL
              AND o.offer_price IS NOT NULL
              AND o.status IN ('approved', 'published')
            ORDER BY o.id
        """),
        {"flyer_id": flyer_id},
    ).mappings().all()

    checked = 0
    applied = 0
    without_original = 0

    for offer in offers:
        checked += 1
        product = db.execute(
            text("SELECT * FROM products WHERE id = :id"),
            {"id": offer["product_id"]},
        ).mappings().first()
        if not product:
            continue

        original = pick_original_price(dict(product), dict(offer))
        if original is None:
            without_original += 1

        if update_product_for_offer(db, cols, dict(offer)):
            applied += 1

    db.commit()
    return {
        "ok": True,
        "flyer_id": flyer_id,
        "checked": checked,
        "applied": applied,
        "without_original": without_original,
        "note": "Products.discounted_price now mirrors flyer offer price. Products.original_price uses flyer original_price when available, otherwise existing product normal price if higher.",
    }


@router.post("/publish-and-apply/{flyer_id}")
def publish_and_apply(user: user_dependency, db: db_dependency, flyer_id: int):
    """
    Publishes approved offers and then applies prices into Products.
    """
    require_admin(user)

    missing = db.execute(
        text("""
            SELECT COUNT(*) FROM flyer_offers
            WHERE flyer_id=:fid
              AND status='approved'
              AND product_id IS NULL
        """),
        {"fid": flyer_id},
    ).scalar() or 0

    if int(missing) > 0:
        raise HTTPException(status_code=400, detail=f"{missing} approved offers have no product_id")

    published = db.execute(
        text("""
            UPDATE flyer_offers
            SET status='published'
            WHERE flyer_id=:fid
              AND status='approved'
              AND product_id IS NOT NULL
        """),
        {"fid": flyer_id},
    ).rowcount or 0

    db.execute(text("UPDATE flyers SET status='published' WHERE id=:fid"), {"fid": flyer_id})
    db.commit()

    # Apply after publish
    cols = product_columns(db)
    offers = db.execute(
        text("""
            SELECT o.*
            FROM flyer_offers o
            WHERE o.flyer_id = :flyer_id
              AND o.product_id IS NOT NULL
              AND o.offer_price IS NOT NULL
              AND o.status IN ('approved', 'published')
            ORDER BY o.id
        """),
        {"flyer_id": flyer_id},
    ).mappings().all()

    checked = 0
    applied = 0
    without_original = 0

    for offer in offers:
        checked += 1
        product = db.execute(
            text("SELECT * FROM products WHERE id = :id"),
            {"id": offer["product_id"]},
        ).mappings().first()
        if not product:
            continue
        if pick_original_price(dict(product), dict(offer)) is None:
            without_original += 1
        if update_product_for_offer(db, cols, dict(offer)):
            applied += 1

    db.commit()

    return {
        "ok": True,
        "flyer_id": flyer_id,
        "published": int(published),
        "checked": checked,
        "applied": applied,
        "without_original": without_original,
    }


@router.post("/clear-expired")
def clear_expired(user: user_dependency, db: db_dependency):
    """
    Optional cleanup for product discounts whose flyer_valid_to is before today.
    It clears discounted_price only where flyer_valid_to is expired.
    """
    require_admin(user)
    cols = product_columns(db)
    if "flyer_valid_to" not in cols or "discounted_price" not in cols:
        return {"ok": True, "cleared": 0, "note": "Missing flyer_valid_to or discounted_price column"}

    today = date.today().isoformat()
    result = db.execute(
        text("""
            UPDATE products
            SET discounted_price = NULL
            WHERE flyer_valid_to IS NOT NULL
              AND flyer_valid_to < :today
        """),
        {"today": today},
    )
    db.commit()
    return {"ok": True, "cleared": int(result.rowcount or 0), "today": today}
