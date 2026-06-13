from __future__ import annotations

import json
import re
import shutil
import unicodedata
import zipfile
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import engine
from app.services.flyer_offer_schema import ensure_flyer_offer_schema


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text_value = unicodedata.normalize("NFKD", value)
    text_value = "".join(ch for ch in text_value if not unicodedata.combining(ch))
    text_value = text_value.lower()
    text_value = text_value.replace("&", " e ")
    text_value = re.sub(r"[^a-z0-9]+", " ", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def slugify(value: str | None, fallback: str = "flyer") -> str:
    normalized = normalize_text(value or fallback)
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return slug or fallback


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).replace("€", "").replace(",", ".")
        cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
        if cleaned in {"", ".", "-"}:
            return None
        return float(cleaned)
    except Exception:
        return None


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y", "si", "sì"}


def get_payload_products(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if not isinstance(payload, dict):
        return []
    products = payload.get("products") or payload.get("offers") or []
    return [p for p in products if isinstance(p, dict)]


def get_retailer(payload: Any) -> str:
    if isinstance(payload, dict):
        return str(payload.get("retailer") or payload.get("supermarket") or payload.get("store") or "Unknown").strip()
    return "Unknown"


def get_title(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        return str(payload.get("title") or payload.get("flyer_title") or fallback).strip()
    return fallback


def get_payload_value(payload: Any, key: str, fallback: Any = None) -> Any:
    if isinstance(payload, dict):
        return payload.get(key, fallback)
    return fallback


def ensure_supermarket(db: Session, retailer: str) -> tuple[int | None, str]:
    row = db.execute(
        text("SELECT id, name FROM supermarkets WHERE lower(name) = lower(:name) LIMIT 1"),
        {"name": retailer},
    ).mappings().first()
    if row:
        return row["id"], row["name"]

    try:
        result = db.execute(
            text("INSERT INTO supermarkets (name, image, location) VALUES (:name, NULL, NULL) RETURNING id"),
            {"name": retailer},
        )
        supermarket_id = result.scalar()
        db.commit()
        return int(supermarket_id), retailer
    except Exception:
        db.rollback()
        # SQLite fallback
        db.execute(
            text("INSERT INTO supermarkets (name, image, location) VALUES (:name, NULL, NULL)"),
            {"name": retailer},
        )
        db.commit()
        row = db.execute(
            text("SELECT id, name FROM supermarkets WHERE lower(name) = lower(:name) LIMIT 1"),
            {"name": retailer},
        ).mappings().first()
        return (int(row["id"]) if row else None), retailer


def create_flyer(db: Session, *, supermarket_id: int | None, retailer: str, title: str, payload: Any) -> int:
    params = {
        "supermarket_id": supermarket_id,
        "retailer": retailer,
        "title": title,
        "valid_from": get_payload_value(payload, "valid_from"),
        "valid_to": get_payload_value(payload, "valid_to"),
        "source": get_payload_value(payload, "source", title),
        "source_url": get_payload_value(payload, "source_url"),
    }

    try:
        result = db.execute(
            text("""
                INSERT INTO flyers (supermarket_id, retailer, title, valid_from, valid_to, source, source_url, status)
                VALUES (:supermarket_id, :retailer, :title, :valid_from, :valid_to, :source, :source_url, 'draft')
                RETURNING id
            """),
            params,
        )
        flyer_id = result.scalar()
        db.commit()
        return int(flyer_id)
    except Exception:
        db.rollback()
        db.execute(
            text("""
                INSERT INTO flyers (supermarket_id, retailer, title, valid_from, valid_to, source, source_url, status)
                VALUES (:supermarket_id, :retailer, :title, :valid_from, :valid_to, :source, :source_url, 'draft')
            """),
            params,
        )
        db.commit()
        row = db.execute(text("SELECT max(id) AS id FROM flyers")).mappings().first()
        return int(row["id"])


def product_rows(db: Session, supermarket_id: int | None) -> list[dict[str, Any]]:
    rows = db.execute(
        text("""
            SELECT id, name, category, unit, supermarket_id, brand
            FROM products
            WHERE (:sid IS NULL OR supermarket_id = :sid)
        """),
        {"sid": supermarket_id},
    ).mappings().all()
    return [dict(row) for row in rows]


def alias_match(db: Session, supermarket_id: int | None, normalized_name: str) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT product_id, confidence
            FROM product_aliases
            WHERE normalized_alias = :alias
              AND (:sid IS NULL OR supermarket_id IS NULL OR supermarket_id = :sid)
            ORDER BY confidence DESC
            LIMIT 1
        """),
        {"alias": normalized_name, "sid": supermarket_id},
    ).mappings().first()
    return dict(row) if row else None


def compute_match_score(raw: dict[str, Any], product: dict[str, Any], normalized_name: str) -> float:
    product_name = normalize_text(product.get("name"))
    score = SequenceMatcher(None, normalized_name, product_name).ratio()

    brand = normalize_text(raw.get("brand"))
    product_brand = normalize_text(product.get("brand"))
    if brand and product_brand and brand == product_brand:
        score += 0.08
    elif brand and brand in product_name:
        score += 0.05

    raw_unit = normalize_text(raw.get("unit"))
    product_unit = normalize_text(product.get("unit"))
    if raw_unit and product_unit and raw_unit == product_unit:
        score += 0.05

    raw_category = normalize_text(raw.get("category"))
    product_category = normalize_text(product.get("category"))
    if raw_category and product_category and raw_category == product_category:
        score += 0.03

    if product_name and (product_name in normalized_name or normalized_name in product_name):
        score += 0.06

    return min(score, 1.0)


def suggest_match(db: Session, raw: dict[str, Any], supermarket_id: int | None) -> tuple[int | None, str, float]:
    normalized_name = normalize_text(raw.get("name") or raw.get("raw_name") or raw.get("product_name"))
    alias = alias_match(db, supermarket_id, normalized_name)
    if alias:
        return int(alias["product_id"]), "auto_matched_alias", float(alias.get("confidence") or 1)

    candidates = product_rows(db, supermarket_id)
    best_id = None
    best_score = 0.0

    for product in candidates:
        score = compute_match_score(raw, product, normalized_name)
        if score > best_score:
            best_score = score
            best_id = int(product["id"])

    if best_id is not None and best_score >= 0.90:
        return best_id, "auto_matched", best_score
    if best_id is not None and best_score >= 0.68:
        return best_id, "needs_review", best_score
    return None, "new_product_suggestion", best_score


def price_type(raw: dict[str, Any]) -> str:
    value = str(raw.get("price_type") or "").lower().strip()
    if value in {"fixed", "weight", "manual"}:
        return value
    unit = str(raw.get("price_unit") or raw.get("unit") or "").lower()
    if unit in {"kg", "etto", "hg", "l", "lt"}:
        return "weight"
    return "fixed"


def price_unit(raw: dict[str, Any], pt: str) -> str:
    value = str(raw.get("price_unit") or "").strip()
    if value:
        return value
    unit = str(raw.get("unit") or "").strip()
    if pt == "weight" and unit.lower() in {"kg", "etto", "hg", "l", "lt"}:
        return unit
    return unit or "pz"


def offer_price(raw: dict[str, Any]) -> float | None:
    for key in ["offer_price", "price", "discounted_price", "original_price"]:
        parsed = parse_float(raw.get(key))
        if parsed is not None and parsed > 0:
            return parsed
    return None


def original_price(raw: dict[str, Any]) -> float | None:
    old = parse_float(raw.get("old_price"))
    if old is not None:
        return old
    value = parse_float(raw.get("original_price"))
    discounted = parse_float(raw.get("discounted_price"))
    if value is not None and discounted is not None and value > discounted:
        return value
    return None


def copy_image_from_zip(z: zipfile.ZipFile, raw: dict[str, Any], target_dir: Path, slug: str) -> str | None:
    source = raw.get("image_path") or raw.get("image") or raw.get("image_url")
    if not source:
        return None

    source = str(source).lstrip("/")
    if source not in z.namelist():
        # Try common product_images prefix.
        alt = f"product_images/{Path(source).name}"
        if alt in z.namelist():
            source = alt
        else:
            return str(raw.get("image_url") or raw.get("image") or "")

    suffix = Path(source).suffix.lower() or ".jpg"
    filename = f"{slug}{suffix}"
    out = target_dir / filename

    with z.open(source) as src, out.open("wb") as dst:
        shutil.copyfileobj(src, dst)

    return f"/static/images/flyer_offers/{target_dir.name}/{filename}"


def insert_offer(db: Session, params: dict[str, Any]) -> int:
    try:
        result = db.execute(
            text("""
                INSERT INTO flyer_offers (
                    flyer_id, product_id, suggested_product_id, raw_name, normalized_name, brand, category, unit,
                    offer_price, original_price, price_type, price_unit, flyer_page, image, valid_from, valid_to,
                    source, source_url, is_loyalty_only, is_from_price, offer_note,
                    match_status, match_score, status
                )
                VALUES (
                    :flyer_id, :product_id, :suggested_product_id, :raw_name, :normalized_name, :brand, :category, :unit,
                    :offer_price, :original_price, :price_type, :price_unit, :flyer_page, :image, :valid_from, :valid_to,
                    :source, :source_url, :is_loyalty_only, :is_from_price, :offer_note,
                    :match_status, :match_score, :status
                )
                RETURNING id
            """),
            params,
        )
        offer_id = result.scalar()
        return int(offer_id)
    except Exception:
        db.rollback()
        db.execute(
            text("""
                INSERT INTO flyer_offers (
                    flyer_id, product_id, suggested_product_id, raw_name, normalized_name, brand, category, unit,
                    offer_price, original_price, price_type, price_unit, flyer_page, image, valid_from, valid_to,
                    source, source_url, is_loyalty_only, is_from_price, offer_note,
                    match_status, match_score, status
                )
                VALUES (
                    :flyer_id, :product_id, :suggested_product_id, :raw_name, :normalized_name, :brand, :category, :unit,
                    :offer_price, :original_price, :price_type, :price_unit, :flyer_page, :image, :valid_from, :valid_to,
                    :source, :source_url, :is_loyalty_only, :is_from_price, :offer_note,
                    :match_status, :match_score, :status
                )
            """),
            params,
        )
        row = db.execute(text("SELECT max(id) AS id FROM flyer_offers")).mappings().first()
        return int(row["id"])


def import_zip_to_draft(db: Session, zip_path: Path, *, import_name: str | None = None) -> dict[str, Any]:
    ensure_flyer_offer_schema(engine)

    if not zip_path.exists():
        raise ValueError(f"ZIP not found: {zip_path}")

    with zipfile.ZipFile(zip_path, "r") as z:
        if "products.json" not in z.namelist():
            raise ValueError("ZIP must contain products.json")

        payload = json.loads(z.read("products.json").decode("utf-8"))
        products = get_payload_products(payload)

        retailer = get_retailer(payload)
        title = get_title(payload, import_name or zip_path.stem)
        supermarket_id, retailer = ensure_supermarket(db, retailer)
        flyer_id = create_flyer(db, supermarket_id=supermarket_id, retailer=retailer, title=title, payload=payload)

        image_folder_name = f"{slugify(title)}_{uuid4().hex[:8]}"
        target_dir = Path("static") / "images" / "flyer_offers" / image_folder_name
        target_dir.mkdir(parents=True, exist_ok=True)

        counters = {
            "created_draft_offers": 0,
            "auto_matched": 0,
            "needs_review": 0,
            "new_product_suggestion": 0,
            "skipped": 0,
        }
        created_ids: list[int] = []
        errors: list[dict[str, Any]] = []

        for index, raw in enumerate(products, start=1):
            raw_name = str(raw.get("name") or raw.get("raw_name") or raw.get("product_name") or "").strip()
            if not raw_name:
                counters["skipped"] += 1
                errors.append({"index": index, "error": "missing name"})
                continue

            price = offer_price(raw)
            if price is None:
                counters["skipped"] += 1
                errors.append({"index": index, "name": raw_name, "error": "missing offer price"})
                continue

            normalized_name = normalize_text(raw_name)
            suggested_id, match_status, score = suggest_match(db, raw, supermarket_id)
            pt = price_type(raw)
            pu = price_unit(raw, pt)
            page = parse_float(raw.get("flyer_page") or raw.get("page"))
            image = copy_image_from_zip(z, raw, target_dir, slugify(raw_name))

            params = {
                "flyer_id": flyer_id,
                "product_id": suggested_id if match_status.startswith("auto_matched") else None,
                "suggested_product_id": suggested_id,
                "raw_name": raw_name,
                "normalized_name": normalized_name,
                "brand": raw.get("brand"),
                "category": raw.get("category") or get_payload_value(payload, "default_category", "Altro"),
                "unit": raw.get("unit") or raw.get("price_unit") or "pz",
                "offer_price": price,
                "original_price": original_price(raw),
                "price_type": pt,
                "price_unit": pu,
                "flyer_page": int(page) if page is not None else None,
                "image": image,
                "valid_from": raw.get("flyer_valid_from") or get_payload_value(payload, "valid_from"),
                "valid_to": raw.get("flyer_valid_to") or get_payload_value(payload, "valid_to"),
                "source": raw.get("source") or get_payload_value(payload, "source", title),
                "source_url": raw.get("source_url") or get_payload_value(payload, "source_url"),
                "is_loyalty_only": parse_bool(raw.get("is_loyalty_only")),
                "is_from_price": parse_bool(raw.get("is_from_price")),
                "offer_note": raw.get("offer_note"),
                "match_status": match_status,
                "match_score": round(score, 4),
                "status": "draft",
            }

            offer_id = insert_offer(db, params)
            created_ids.append(offer_id)
            counters["created_draft_offers"] += 1

            if match_status.startswith("auto_matched"):
                counters["auto_matched"] += 1
            elif match_status == "needs_review":
                counters["needs_review"] += 1
            else:
                counters["new_product_suggestion"] += 1

        db.commit()

    return {
        "flyer_id": flyer_id,
        "retailer": retailer,
        "title": title,
        "products_in_json": len(products),
        "offer_ids": created_ids,
        "errors": errors,
        **counters,
    }


def create_product_from_offer(db: Session, offer_id: int, *, create_alias: bool = True) -> int:
    offer = db.execute(text("SELECT * FROM flyer_offers WHERE id = :id"), {"id": offer_id}).mappings().first()
    if not offer:
        raise ValueError("Offer not found")

    supermarket_id = db.execute(
        text("SELECT supermarket_id FROM flyers WHERE id = :id"),
        {"id": offer["flyer_id"]},
    ).scalar()

    # Product gets stable/catalog info. Price is initialized from offer_price, but active offer lives in flyer_offers.
    params = {
        "name": offer["raw_name"],
        "category": offer["category"] or "Altro",
        "original_price": offer["offer_price"],
        "discounted_price": None,
        "unit": offer["unit"] or offer["price_unit"] or "pz",
        "supermarket_id": supermarket_id,
        "aisle_order": offer["flyer_page"] or 999,
        "image": offer["image"],
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

    columns = [row["name"] for row in db.execute(text("""
        SELECT column_name AS name FROM information_schema.columns WHERE table_name='products'
    """)).mappings().all()] if engine.dialect.name == "postgresql" else [
        row["name"] for row in db.execute(text("PRAGMA table_info(products)")).mappings().all()
    ]

    base_fields = ["name", "category", "original_price", "discounted_price", "unit", "supermarket_id", "aisle_order", "image"]
    optional = [k for k in params.keys() if k in columns and k not in base_fields]
    fields = base_fields + optional

    sql = f"INSERT INTO products ({', '.join(fields)}) VALUES ({', '.join(':'+f for f in fields)})"
    if engine.dialect.name == "postgresql":
        sql += " RETURNING id"
        product_id = db.execute(text(sql), {k: params[k] for k in fields}).scalar()
    else:
        db.execute(text(sql), {k: params[k] for k in fields})
        product_id = db.execute(text("SELECT max(id) FROM products")).scalar()

    db.execute(
        text("UPDATE flyer_offers SET product_id=:pid, suggested_product_id=:pid, match_status='created_product', status='approved' WHERE id=:oid"),
        {"pid": product_id, "oid": offer_id},
    )

    if create_alias:
        add_alias(db, product_id=int(product_id), supermarket_id=supermarket_id, alias_name=offer["raw_name"])

    db.commit()
    return int(product_id)


def add_alias(db: Session, *, product_id: int, supermarket_id: int | None, alias_name: str) -> None:
    normalized = normalize_text(alias_name)
    existing = db.execute(
        text("SELECT id FROM product_aliases WHERE product_id=:pid AND normalized_alias=:alias LIMIT 1"),
        {"pid": product_id, "alias": normalized},
    ).first()
    if existing:
        return

    db.execute(
        text("""
            INSERT INTO product_aliases (supermarket_id, product_id, alias_name, normalized_alias, confidence)
            VALUES (:sid, :pid, :alias_name, :normalized, 1)
        """),
        {"sid": supermarket_id, "pid": product_id, "alias_name": alias_name, "normalized": normalized},
    )


def associate_offer(db: Session, *, offer_id: int, product_id: int, create_alias: bool = True) -> None:
    offer = db.execute(text("SELECT * FROM flyer_offers WHERE id=:id"), {"id": offer_id}).mappings().first()
    if not offer:
        raise ValueError("Offer not found")

    flyer = db.execute(text("SELECT * FROM flyers WHERE id=:id"), {"id": offer["flyer_id"]}).mappings().first()
    product = db.execute(text("SELECT id FROM products WHERE id=:id"), {"id": product_id}).first()
    if not product:
        raise ValueError("Product not found")

    db.execute(
        text("""
            UPDATE flyer_offers
            SET product_id=:pid, suggested_product_id=:pid, match_status='manual_matched', status='approved'
            WHERE id=:oid
        """),
        {"pid": product_id, "oid": offer_id},
    )
    if create_alias:
        add_alias(db, product_id=product_id, supermarket_id=flyer["supermarket_id"] if flyer else None, alias_name=offer["raw_name"])
    db.commit()
