from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, asdict
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.models import Products, Supermarkets


ImageResolver = Callable[[dict[str, Any], str], Optional[str]]


@dataclass
class ImportSummary:
    retailer: str
    supermarket_id: int
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] | None = None
    products: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_name(name: str, brand: str | None = None) -> str:
    name = re.sub(r"\s+", " ", name or "").strip()
    brand = re.sub(r"\s+", " ", brand or "").strip()

    if brand and brand.lower() not in name.lower():
        return f"{brand} {name}".strip()
    return name


def clean_unit(item: dict[str, Any]) -> str:
    unit = item.get("unit") or item.get("quantity") or item.get("pack_size") or "pz"
    unit = re.sub(r"\s+", " ", str(unit)).strip()
    return unit or "pz"


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).strip().replace("€", "").replace(",", ".")
        cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
        if cleaned in {"", ".", "-"}:
            return None
        return float(cleaned)
    except ValueError:
        return None


def derive_prices(item: dict[str, Any]) -> tuple[float | None, float | None]:
    """
    Converts flyer fields to the app's current Product price model.

    App meaning:
    - original_price: displayed regular price
    - discounted_price: displayed offer price, only when there is a known old price

    Accepted input alternatives:
    - price + old_price
    - discounted_price + original_price
    - price only
    """
    price = parse_float(item.get("price"))
    old_price = parse_float(item.get("old_price"))
    original_price = parse_float(item.get("original_price"))
    discounted_price = parse_float(item.get("discounted_price"))

    if original_price is not None:
        if discounted_price is not None and discounted_price < original_price:
            return original_price, discounted_price
        return original_price, None

    if old_price is not None and price is not None and price < old_price:
        return old_price, price

    if price is not None:
        return price, None

    if discounted_price is not None:
        return discounted_price, None

    return None, None


def ensure_supermarket(db: Session, retailer: str, create_missing: bool = True) -> Supermarkets:
    retailer = re.sub(r"\s+", " ", retailer or "").strip()
    if not retailer:
        raise ValueError("retailer is required")

    existing = (
        db.query(Supermarkets)
        .filter(Supermarkets.name.ilike(retailer))
        .first()
    )
    if existing:
        return existing

    if not create_missing:
        raise ValueError(f"Supermarket not found: {retailer}")

    supermarket = Supermarkets(name=retailer, image=None, location=None)
    db.add(supermarket)
    db.commit()
    db.refresh(supermarket)
    return supermarket


def find_existing_product(db: Session, supermarket_id: int, name: str, unit: str) -> Products | None:
    """
    Lightweight duplicate detection.
    First tries exact case-insensitive name + unit, then exact name only.
    """
    product = (
        db.query(Products)
        .filter(Products.supermarket_id == supermarket_id)
        .filter(Products.name.ilike(name))
        .filter(Products.unit.ilike(unit))
        .first()
    )
    if product:
        return product

    return (
        db.query(Products)
        .filter(Products.supermarket_id == supermarket_id)
        .filter(Products.name.ilike(name))
        .first()
    )


def import_flyer_catalog(
    db: Session,
    payload: dict[str, Any],
    *,
    image_resolver: ImageResolver | None = None,
    update_existing: bool = True,
    create_supermarket: bool = True,
) -> dict[str, Any]:
    retailer = payload.get("retailer") or payload.get("supermarket") or payload.get("store")
    supermarket = ensure_supermarket(db, str(retailer or ""), create_missing=create_supermarket)

    items = payload.get("products") or payload.get("offers") or []
    if not isinstance(items, list):
        raise ValueError("payload must contain a list field named 'products' or 'offers'")

    summary = ImportSummary(
        retailer=supermarket.name,
        supermarket_id=supermarket.id,
        errors=[],
        products=[],
    )

    for index, raw_item in enumerate(items, start=1):
        if not isinstance(raw_item, dict):
            summary.skipped += 1
            summary.errors.append({"index": index, "error": "item is not an object"})
            continue

        brand = raw_item.get("brand")
        raw_name = raw_item.get("name") or raw_item.get("product_name") or raw_item.get("raw_name")
        name = clean_name(str(raw_name or ""), str(brand or "") if brand else None)

        if not name:
            summary.skipped += 1
            summary.errors.append({"index": index, "error": "missing product name"})
            continue

        unit = clean_unit(raw_item)
        category = str(raw_item.get("category") or payload.get("default_category") or "Altro").strip() or "Altro"
        original_price, discounted_price = derive_prices(raw_item)

        if original_price is None or original_price <= 0:
            summary.skipped += 1
            summary.errors.append({"index": index, "name": name, "error": "missing or invalid price"})
            continue

        image_url = None
        if image_resolver:
            image_url = image_resolver(raw_item, name)
        if not image_url:
            image_url = raw_item.get("image") or raw_item.get("image_url") or raw_item.get("image_path")

        aisle_order = parse_float(raw_item.get("aisle_order"))
        if aisle_order is None:
            page = parse_float(raw_item.get("page"))
            aisle_order = page if page is not None else 999.0

        existing = find_existing_product(db, supermarket.id, name, unit)

        if existing and update_existing:
            existing.category = category
            existing.original_price = original_price
            existing.discounted_price = discounted_price
            existing.unit = unit
            existing.aisle_order = aisle_order
            if image_url:
                existing.image = image_url
            summary.updated += 1
            product = existing
        elif existing and not update_existing:
            summary.skipped += 1
            product = existing
        else:
            product = Products(
                name=name,
                category=category,
                original_price=original_price,
                discounted_price=discounted_price,
                unit=unit,
                supermarket_id=supermarket.id,
                aisle_order=aisle_order,
                image=image_url,
                calories=None,
                fat=None,
                carbs=None,
                protein=None,
                location=None,
            )
            db.add(product)
            db.flush()
            summary.created += 1

        summary.products.append({
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "unit": product.unit,
            "original_price": product.original_price,
            "discounted_price": product.discounted_price,
            "image": product.image,
            "created_or_updated": "updated" if existing and update_existing else "created" if not existing else "skipped_existing",
        })

    db.commit()
    return summary.to_dict()
