from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path
from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import engine

PLACEHOLDER_VALUES = {
    "", "placeholder", "/static/images/placeholder.jpg", "static/images/placeholder.jpg",
    "/static/images/products/placeholder.jpg", "static/images/products/placeholder.jpg",
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    t = unicodedata.normalize("NFKD", value)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t.lower()).strip("-")
    return t or "product"


def is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    v = value.strip().lower()
    return v in PLACEHOLDER_VALUES or "placeholder" in v


def product_columns(db: Session) -> set[str]:
    if engine.dialect.name == "postgresql":
        rows = db.execute(text("SELECT column_name AS name FROM information_schema.columns WHERE table_name='products'")).mappings().all()
        return {r["name"] for r in rows}
    rows = db.execute(text("PRAGMA table_info(products)")).mappings().all()
    return {r["name"] for r in rows}


def local_path_from_image(image: str | None) -> Path | None:
    if not image or image.startswith("http://") or image.startswith("https://"):
        return None
    rel = image.lstrip("/")
    if not rel:
        return None
    return Path.cwd() / rel


def copy_offer_image_to_product_image(offer_image: str | None, product_name: str) -> str | None:
    """Copy flyer crop to product image folders and return DB image path."""
    if not offer_image or is_placeholder(offer_image):
        return None
    if offer_image.startswith("http://") or offer_image.startswith("https://"):
        return offer_image

    src = local_path_from_image(offer_image)
    if not src or not src.exists() or not src.is_file():
        # keep non-placeholder path rather than replacing with placeholder
        return offer_image

    suffix = src.suffix.lower() or ".jpg"
    filename = f"{normalize_text(product_name)}{suffix}"
    backend_dir = Path("static") / "images" / "products"
    frontend_dir = Path("frontend") / "static" / "images" / "products"
    backend_dir.mkdir(parents=True, exist_ok=True)
    frontend_dir.mkdir(parents=True, exist_ok=True)
    backend_dest = backend_dir / filename
    frontend_dest = frontend_dir / filename
    shutil.copy2(src, backend_dest)
    try:
        shutil.copy2(src, frontend_dest)
    except Exception:
        pass
    return f"/static/images/products/{filename}"


def add_alias(db: Session, *, product_id: int, supermarket_id: int | None, alias_name: str) -> None:
    normalized = " ".join(re.sub(r"[^a-z0-9]+", " ", alias_name.lower()).split())
    exists = db.execute(
        text("SELECT id FROM product_aliases WHERE product_id=:pid AND normalized_alias=:alias LIMIT 1"),
        {"pid": product_id, "alias": normalized},
    ).first()
    if exists:
        return
    db.execute(
        text("""
            INSERT INTO product_aliases (supermarket_id, product_id, alias_name, normalized_alias, confidence)
            VALUES (:sid, :pid, :alias_name, :normalized, 1)
        """),
        {"sid": supermarket_id, "pid": product_id, "alias_name": alias_name, "normalized": normalized},
    )


def create_product_from_offer_v26e(db: Session, offer_id: int, *, create_alias: bool = True) -> int:
    offer = db.execute(text("SELECT * FROM flyer_offers WHERE id=:id"), {"id": offer_id}).mappings().first()
    if not offer:
        raise ValueError("Offer not found")
    flyer = db.execute(text("SELECT * FROM flyers WHERE id=:id"), {"id": offer["flyer_id"]}).mappings().first()
    supermarket_id = flyer["supermarket_id"] if flyer else None
    image = copy_offer_image_to_product_image(offer["image"], offer["raw_name"]) or offer["image"]

    params: dict[str, Any] = {
        "name": offer["raw_name"],
        "category": offer["category"] or "Altro",
        "original_price": offer["offer_price"],
        "discounted_price": None,
        "unit": offer["unit"] or offer["price_unit"] or "pz",
        "supermarket_id": supermarket_id,
        "aisle_order": offer["flyer_page"] or 999,
        "image": image,
        "brand": offer["brand"],
        "price_type": offer["price_type"],
        "price_unit": offer["price_unit"],
        "flyer_page": offer["flyer_page"],
        "flyer_valid_from": offer["valid_from"],
        "flyer_valid_to": offer["valid_to"],
        "flyer_source": offer["source"],
        "flyer_source_url": offer["source_url"],
        "offer_note": offer["offer_note"],
    }
    cols = product_columns(db)
    base_fields = ["name", "category", "original_price", "discounted_price", "unit", "supermarket_id", "aisle_order", "image"]
    fields = base_fields + [k for k in params if k in cols and k not in base_fields]
    sql = f"INSERT INTO products ({', '.join(fields)}) VALUES ({', '.join(':'+f for f in fields)})"
    values = {k: params[k] for k in fields}
    if engine.dialect.name == "postgresql":
        product_id = db.execute(text(sql + " RETURNING id"), values).scalar()
    else:
        db.execute(text(sql), values)
        product_id = db.execute(text("SELECT max(id) FROM products")).scalar()
    db.execute(
        text("UPDATE flyer_offers SET product_id=:pid, suggested_product_id=:pid, match_status='created_product', status='approved' WHERE id=:oid"),
        {"pid": product_id, "oid": offer_id},
    )
    if create_alias:
        add_alias(db, product_id=int(product_id), supermarket_id=supermarket_id, alias_name=offer["raw_name"])
    db.commit()
    return int(product_id)


def associate_offer_v26e(db: Session, *, offer_id: int, product_id: int, create_alias: bool = True, match_status: str = "manual_matched") -> None:
    offer = db.execute(text("SELECT * FROM flyer_offers WHERE id=:id"), {"id": offer_id}).mappings().first()
    if not offer:
        raise ValueError("Offer not found")
    flyer = db.execute(text("SELECT * FROM flyers WHERE id=:id"), {"id": offer["flyer_id"]}).mappings().first()
    if not db.execute(text("SELECT id FROM products WHERE id=:id"), {"id": product_id}).first():
        raise ValueError("Product not found")
    db.execute(
        text("UPDATE flyer_offers SET product_id=:pid, suggested_product_id=:pid, match_status=:ms, status='approved' WHERE id=:oid"),
        {"pid": product_id, "oid": offer_id, "ms": match_status},
    )
    if create_alias:
        add_alias(db, product_id=product_id, supermarket_id=flyer["supermarket_id"] if flyer else None, alias_name=offer["raw_name"])
    db.commit()


def bulk_associate_suggested_v26e(db: Session, offer_ids: list[int], *, create_alias: bool = True) -> dict[str, Any]:
    associated = skipped = 0
    for offer_id in offer_ids:
        offer = db.execute(text("SELECT suggested_product_id FROM flyer_offers WHERE id=:id"), {"id": offer_id}).mappings().first()
        if not offer or not offer["suggested_product_id"]:
            skipped += 1
            continue
        associate_offer_v26e(db, offer_id=offer_id, product_id=int(offer["suggested_product_id"]), create_alias=create_alias, match_status="bulk_matched")
        associated += 1
    return {"associated": associated, "skipped": skipped}


def bulk_create_products_v26e(db: Session, offer_ids: list[int]) -> dict[str, Any]:
    created = skipped = 0
    product_ids: list[int] = []
    for offer_id in offer_ids:
        offer = db.execute(text("SELECT product_id FROM flyer_offers WHERE id=:id"), {"id": offer_id}).mappings().first()
        if not offer or offer["product_id"]:
            skipped += 1
            continue
        try:
            product_ids.append(create_product_from_offer_v26e(db, offer_id))
            created += 1
        except Exception:
            db.rollback()
            skipped += 1
    return {"created": created, "skipped": skipped, "product_ids": product_ids}


def bulk_approve_offers_v26e(db: Session, offer_ids: list[int]) -> dict[str, Any]:
    if not offer_ids:
        return {"approved": 0, "skipped": 0}
    params = {f"id{i}": int(v) for i, v in enumerate(offer_ids)}
    placeholders = ", ".join(f":{k}" for k in params)
    res = db.execute(text(f"UPDATE flyer_offers SET status='approved' WHERE id IN ({placeholders}) AND product_id IS NOT NULL"), params)
    db.commit()
    approved = int(res.rowcount or 0)
    return {"approved": approved, "skipped": len(offer_ids) - approved}


def bulk_reject_offers_v26e(db: Session, offer_ids: list[int]) -> dict[str, Any]:
    if not offer_ids:
        return {"rejected": 0}
    params = {f"id{i}": int(v) for i, v in enumerate(offer_ids)}
    placeholders = ", ".join(f":{k}" for k in params)
    res = db.execute(text(f"UPDATE flyer_offers SET status='rejected' WHERE id IN ({placeholders})"), params)
    db.commit()
    return {"rejected": int(res.rowcount or 0)}


def repair_product_images_from_offers_v26e(db: Session, flyer_id: int | None = None) -> dict[str, Any]:
    where = ["o.product_id IS NOT NULL", "o.image IS NOT NULL"]
    params: dict[str, Any] = {}
    if flyer_id is not None:
        where.append("o.flyer_id = :flyer_id")
        params["flyer_id"] = flyer_id
    rows = db.execute(text(f"""
        SELECT o.id AS offer_id, o.raw_name, o.image AS offer_image,
               p.id AS product_id, p.name AS product_name, p.image AS product_image
        FROM flyer_offers o
        JOIN products p ON p.id = o.product_id
        WHERE {' AND '.join(where)}
    """), params).mappings().all()
    repaired = skipped = 0
    for row in rows:
        if not is_placeholder(row["product_image"]):
            skipped += 1
            continue
        new_image = copy_offer_image_to_product_image(row["offer_image"], row["product_name"] or row["raw_name"])
        if not new_image or is_placeholder(new_image):
            skipped += 1
            continue
        db.execute(text("UPDATE products SET image=:image WHERE id=:id"), {"image": new_image, "id": row["product_id"]})
        repaired += 1
    db.commit()
    return {"repaired": repaired, "skipped": skipped, "checked": len(rows)}
