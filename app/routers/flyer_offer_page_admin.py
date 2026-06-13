from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.routers.auth import get_current_user
from app.services.flyer_offer_schema import ensure_flyer_offer_schema


router = APIRouter(prefix="/admin/flyer-offers-page", tags=["admin-flyer-offers-page"])


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


class BulkRequest(BaseModel):
    offer_ids: list[int] = Field(default_factory=list)
    create_alias: bool = True


class AssociateRequest(BaseModel):
    product_id: int
    create_alias: bool = True


class RepairRequest(BaseModel):
    flyer_id: Optional[int] = None


PLACEHOLDER_VALUES = {
    "",
    "placeholder",
    "/static/images/placeholder.jpg",
    "static/images/placeholder.jpg",
    "/static/images/products/placeholder.jpg",
    "static/images/products/placeholder.jpg",
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text_value = unicodedata.normalize("NFKD", value)
    text_value = "".join(ch for ch in text_value if not unicodedata.combining(ch))
    text_value = text_value.lower()
    text_value = text_value.replace("&", " e ")
    text_value = re.sub(r"[^a-z0-9]+", " ", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def slugify(value: str | None, fallback: str = "product") -> str:
    normalized = normalize_text(value or fallback)
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return slug[:150] or fallback


def q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def product_columns(db: Session) -> set[str]:
    if engine.dialect.name == "postgresql":
        rows = db.execute(
            text("SELECT column_name AS name FROM information_schema.columns WHERE table_name='products'")
        ).mappings().all()
        return {row["name"] for row in rows}
    rows = db.execute(text("PRAGMA table_info(products)")).mappings().all()
    return {row["name"] for row in rows}


def bind_ids(ids: list[int]) -> tuple[str, dict[str, int]]:
    clean = [int(x) for x in ids if int(x) > 0]
    if not clean:
        raise HTTPException(status_code=400, detail="No offer_ids supplied")
    params = {f"id{i}": value for i, value in enumerate(clean)}
    placeholders = ", ".join(f":{key}" for key in params)
    return placeholders, params


def image_is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    return normalized in PLACEHOLDER_VALUES or "placeholder" in normalized


def path_from_static_url(image: str | None) -> Path | None:
    if not image:
        return None
    if image.startswith("http://") or image.startswith("https://"):
        return None
    rel = image.lstrip("/")
    if not rel:
        return None
    return Path(rel)


def copy_offer_image_to_product_image(offer_image: str | None, product_name: str) -> str | None:
    if not offer_image or image_is_placeholder(offer_image):
        return None

    if offer_image.startswith("http://") or offer_image.startswith("https://"):
        return offer_image

    src_rel = path_from_static_url(offer_image)
    if not src_rel:
        return offer_image

    src = Path.cwd() / src_rel
    if not src.exists() or not src.is_file():
        # Keep the useful path in DB; do not replace with placeholder.
        return offer_image

    suffix = src.suffix.lower() or ".jpg"
    filename = f"{slugify(product_name)}{suffix}"

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
    normalized = normalize_text(alias_name)
    if not normalized:
        return

    existing = db.execute(
        text("""
            SELECT id FROM product_aliases
            WHERE product_id = :pid
              AND normalized_alias = :alias
            LIMIT 1
        """),
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


def create_product_from_offer_sql(db: Session, offer_id: int, *, create_alias: bool = True) -> int:
    offer = db.execute(text("SELECT * FROM flyer_offers WHERE id = :id"), {"id": offer_id}).mappings().first()
    if not offer:
        raise HTTPException(status_code=404, detail=f"Offer {offer_id} not found")

    if offer["product_id"]:
        return int(offer["product_id"])

    flyer = db.execute(text("SELECT * FROM flyers WHERE id = :id"), {"id": offer["flyer_id"]}).mappings().first()
    supermarket_id = flyer["supermarket_id"] if flyer else None
    product_image = copy_offer_image_to_product_image(offer["image"], offer["raw_name"]) or offer["image"]

    params: dict[str, Any] = {
        "name": offer["raw_name"],
        "category": offer["category"] or "Altro",
        "original_price": offer["offer_price"],
        "discounted_price": None,
        "unit": offer["unit"] or offer["price_unit"] or "pz",
        "supermarket_id": supermarket_id,
        "aisle_order": offer["flyer_page"] or 999,
        "image": product_image,
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
    base_fields = [
        "name",
        "category",
        "original_price",
        "discounted_price",
        "unit",
        "supermarket_id",
        "aisle_order",
        "image",
    ]
    optional_fields = [key for key in params if key in cols and key not in base_fields]
    fields = [field for field in base_fields if field in cols] + optional_fields

    sql = f"INSERT INTO products ({', '.join(fields)}) VALUES ({', '.join(':'+field for field in fields)})"
    values = {field: params[field] for field in fields}

    if engine.dialect.name == "postgresql":
        sql += " RETURNING id"
        product_id = db.execute(text(sql), values).scalar()
    else:
        db.execute(text(sql), values)
        product_id = db.execute(text("SELECT max(id) FROM products")).scalar()

    db.execute(
        text("""
            UPDATE flyer_offers
            SET product_id = :pid,
                suggested_product_id = :pid,
                match_status = 'created_product',
                status = 'approved'
            WHERE id = :oid
        """),
        {"pid": product_id, "oid": offer_id},
    )

    if create_alias:
        add_alias(db, product_id=int(product_id), supermarket_id=supermarket_id, alias_name=offer["raw_name"])

    return int(product_id)


@router.get("/flyers")
def list_flyers(user: user_dependency, db: db_dependency, limit: int = 50):
    require_admin(user)

    rows = db.execute(
        text("""
            SELECT f.*,
                   COUNT(o.id) AS offers_count,
                   SUM(CASE WHEN o.match_status LIKE 'auto_matched%' OR o.match_status = 'bulk_matched' THEN 1 ELSE 0 END) AS auto_matched_count,
                   SUM(CASE WHEN o.match_status = 'needs_review' THEN 1 ELSE 0 END) AS needs_review_count,
                   SUM(CASE WHEN o.match_status = 'new_product_suggestion' THEN 1 ELSE 0 END) AS new_product_count,
                   SUM(CASE WHEN o.status = 'approved' THEN 1 ELSE 0 END) AS approved_count,
                   SUM(CASE WHEN o.status = 'published' THEN 1 ELSE 0 END) AS published_count,
                   SUM(CASE WHEN o.status = 'rejected' THEN 1 ELSE 0 END) AS rejected_count
            FROM flyers f
            LEFT JOIN flyer_offers o ON o.flyer_id = f.id
            GROUP BY f.id
            ORDER BY f.id DESC
            LIMIT :limit
        """),
        {"limit": min(max(limit, 1), 100)},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.get("/flyers/{flyer_id}/offers")
def list_offers(
    user: user_dependency,
    db: db_dependency,
    flyer_id: int,
    offset: int = 0,
    limit: int = 25,
    match_status: Optional[str] = None,
    status_filter: Optional[str] = None,
):
    require_admin(user)

    offset = max(offset, 0)
    limit = min(max(limit, 1), 80)

    where = ["o.flyer_id = :flyer_id"]
    params: dict[str, Any] = {"flyer_id": flyer_id, "offset": offset, "limit": limit}

    if match_status:
        where.append("o.match_status = :match_status")
        params["match_status"] = match_status
    if status_filter:
        where.append("o.status = :status_filter")
        params["status_filter"] = status_filter

    where_sql = " AND ".join(where)

    total = db.execute(
        text(f"SELECT COUNT(*) FROM flyer_offers o WHERE {where_sql}"),
        params,
    ).scalar() or 0

    rows = db.execute(
        text(f"""
            SELECT o.id, o.flyer_id, o.product_id, o.suggested_product_id,
                   o.raw_name, o.brand, o.category, o.unit,
                   o.offer_price, o.original_price, o.price_type, o.price_unit,
                   o.flyer_page, o.image, o.valid_from, o.valid_to,
                   o.match_status, o.match_score, o.status,
                   p.name AS product_name,
                   sp.name AS suggested_product_name
            FROM flyer_offers o
            LEFT JOIN products p ON p.id = o.product_id
            LEFT JOIN products sp ON sp.id = o.suggested_product_id
            WHERE {where_sql}
            ORDER BY o.flyer_page ASC NULLS LAST, o.id ASC
            LIMIT :limit OFFSET :offset
        """),
        params,
    ).mappings().all()

    return {
        "items": [dict(row) for row in rows],
        "total": int(total),
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < int(total),
    }


@router.get("/products/search")
def product_search(user: user_dependency, db: db_dependency, q: str, limit: int = 20):
    require_admin(user)
    rows = db.execute(
        text("""
            SELECT p.id, p.name, p.category, p.unit, p.image, p.original_price, p.discounted_price,
                   s.name AS supermarket_name
            FROM products p
            LEFT JOIN supermarkets s ON s.id = p.supermarket_id
            WHERE lower(p.name) LIKE lower(:q)
            ORDER BY p.name
            LIMIT :limit
        """),
        {"q": f"%{q}%", "limit": min(max(limit, 1), 50)},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/offers/{offer_id}/associate")
def associate_offer(user: user_dependency, db: db_dependency, offer_id: int, request: AssociateRequest):
    require_admin(user)

    offer = db.execute(text("SELECT * FROM flyer_offers WHERE id=:id"), {"id": offer_id}).mappings().first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    product = db.execute(text("SELECT id FROM products WHERE id=:id"), {"id": request.product_id}).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    flyer = db.execute(text("SELECT * FROM flyers WHERE id=:id"), {"id": offer["flyer_id"]}).mappings().first()

    db.execute(
        text("""
            UPDATE flyer_offers
            SET product_id=:pid,
                suggested_product_id=:pid,
                match_status='manual_matched',
                status='approved'
            WHERE id=:oid
        """),
        {"pid": request.product_id, "oid": offer_id},
    )

    if request.create_alias:
        add_alias(
            db,
            product_id=request.product_id,
            supermarket_id=flyer["supermarket_id"] if flyer else None,
            alias_name=offer["raw_name"],
        )

    db.commit()
    return {"ok": True}


@router.post("/offers/{offer_id}/create-product")
def create_product(user: user_dependency, db: db_dependency, offer_id: int):
    require_admin(user)
    product_id = create_product_from_offer_sql(db, offer_id)
    db.commit()
    return {"ok": True, "product_id": product_id}


@router.post("/offers/{offer_id}/reject")
def reject_offer(user: user_dependency, db: db_dependency, offer_id: int):
    require_admin(user)
    result = db.execute(text("UPDATE flyer_offers SET status='rejected' WHERE id=:id"), {"id": offer_id})
    db.commit()
    return {"ok": True, "rejected": int(result.rowcount or 0)}


@router.post("/offers/bulk-approve")
def bulk_approve(user: user_dependency, db: db_dependency, request: BulkRequest):
    require_admin(user)
    placeholders, params = bind_ids(request.offer_ids)
    result = db.execute(
        text(f"""
            UPDATE flyer_offers
            SET status = 'approved'
            WHERE id IN ({placeholders})
              AND product_id IS NOT NULL
        """),
        params,
    )
    db.commit()
    approved = int(result.rowcount or 0)
    return {"ok": True, "approved": approved, "skipped": len(request.offer_ids) - approved}


@router.post("/offers/bulk-associate-suggested")
def bulk_associate_suggested(user: user_dependency, db: db_dependency, request: BulkRequest):
    require_admin(user)
    placeholders, params = bind_ids(request.offer_ids)

    rows = db.execute(
        text(f"""
            SELECT o.*, f.supermarket_id
            FROM flyer_offers o
            JOIN flyers f ON f.id = o.flyer_id
            WHERE o.id IN ({placeholders})
              AND o.suggested_product_id IS NOT NULL
        """),
        params,
    ).mappings().all()

    associated = 0
    for row in rows:
        product_id = int(row["suggested_product_id"])
        db.execute(
            text("""
                UPDATE flyer_offers
                SET product_id=:pid,
                    match_status='bulk_matched',
                    status='approved'
                WHERE id=:oid
            """),
            {"pid": product_id, "oid": row["id"]},
        )
        if request.create_alias:
            add_alias(
                db,
                product_id=product_id,
                supermarket_id=row["supermarket_id"],
                alias_name=row["raw_name"],
            )
        associated += 1

    db.commit()
    return {"ok": True, "associated": associated, "skipped": len(request.offer_ids) - associated}


@router.post("/offers/bulk-create-products")
def bulk_create_products(user: user_dependency, db: db_dependency, request: BulkRequest):
    require_admin(user)
    created = 0
    skipped = 0
    product_ids: list[int] = []

    for offer_id in request.offer_ids:
        try:
            row = db.execute(
                text("SELECT id, product_id FROM flyer_offers WHERE id=:id"),
                {"id": offer_id},
            ).mappings().first()
            if not row or row["product_id"]:
                skipped += 1
                continue
            product_id = create_product_from_offer_sql(db, int(offer_id), create_alias=request.create_alias)
            product_ids.append(product_id)
            created += 1
        except Exception:
            db.rollback()
            skipped += 1

    db.commit()
    return {"ok": True, "created": created, "skipped": skipped, "product_ids": product_ids}


@router.post("/offers/bulk-reject")
def bulk_reject(user: user_dependency, db: db_dependency, request: BulkRequest):
    require_admin(user)
    placeholders, params = bind_ids(request.offer_ids)
    result = db.execute(
        text(f"UPDATE flyer_offers SET status='rejected' WHERE id IN ({placeholders})"),
        params,
    )
    db.commit()
    return {"ok": True, "rejected": int(result.rowcount or 0)}


@router.post("/flyers/{flyer_id}/approve-auto")
def approve_auto(user: user_dependency, db: db_dependency, flyer_id: int):
    require_admin(user)
    result = db.execute(
        text("""
            UPDATE flyer_offers
            SET status='approved'
            WHERE flyer_id=:fid
              AND product_id IS NOT NULL
              AND (match_status LIKE 'auto_matched%' OR match_status='bulk_matched')
              AND status='draft'
        """),
        {"fid": flyer_id},
    )
    db.commit()
    return {"ok": True, "approved": int(result.rowcount or 0)}


@router.post("/flyers/{flyer_id}/publish")
def publish_flyer(user: user_dependency, db: db_dependency, flyer_id: int):
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

    result = db.execute(
        text("""
            UPDATE flyer_offers
            SET status='published'
            WHERE flyer_id=:fid
              AND status='approved'
              AND product_id IS NOT NULL
        """),
        {"fid": flyer_id},
    )
    db.execute(text("UPDATE flyers SET status='published' WHERE id=:fid"), {"fid": flyer_id})
    db.commit()
    return {"ok": True, "published": int(result.rowcount or 0)}


@router.post("/repair-product-images")
def repair_product_images(user: user_dependency, db: db_dependency, request: RepairRequest):
    require_admin(user)

    where = ["o.product_id IS NOT NULL", "o.image IS NOT NULL"]
    params: dict[str, Any] = {}
    if request.flyer_id is not None:
        where.append("o.flyer_id = :flyer_id")
        params["flyer_id"] = request.flyer_id

    rows = db.execute(
        text(f"""
            SELECT o.id AS offer_id, o.raw_name, o.image AS offer_image,
                   p.id AS product_id, p.name AS product_name, p.image AS product_image
            FROM flyer_offers o
            JOIN products p ON p.id = o.product_id
            WHERE {' AND '.join(where)}
        """),
        params,
    ).mappings().all()

    repaired = 0
    skipped = 0

    for row in rows:
        if not image_is_placeholder(row["product_image"]):
            skipped += 1
            continue

        new_image = copy_offer_image_to_product_image(row["offer_image"], row["product_name"] or row["raw_name"])
        if not new_image or image_is_placeholder(new_image):
            skipped += 1
            continue

        db.execute(
            text("UPDATE products SET image=:image WHERE id=:id"),
            {"image": new_image, "id": row["product_id"]},
        )
        repaired += 1

    db.commit()
    return {"ok": True, "checked": len(rows), "repaired": repaired, "skipped": skipped}
