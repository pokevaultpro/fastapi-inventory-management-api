from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette import status

from app.database import SessionLocal, engine
from app.routers.auth import get_current_user
from app.services.flyer_offer_importer import associate_offer, create_product_from_offer, import_zip_to_draft
from app.services.flyer_offer_schema import ensure_flyer_offer_schema, schema_debug


router = APIRouter(prefix="/admin/flyer-offers", tags=["admin-flyer-offers"])
_schema_ready = False


def ensure_ready() -> None:
    global _schema_ready
    if not _schema_ready:
        ensure_flyer_offer_schema(engine)
        _schema_ready = True


def get_db():
    ensure_ready()
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


class AssociateRequest(BaseModel):
    product_id: int
    create_alias: bool = True


class OfferPatch(BaseModel):
    raw_name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    offer_price: Optional[float] = None
    original_price: Optional[float] = None
    price_type: Optional[str] = None
    price_unit: Optional[str] = None
    flyer_page: Optional[int] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    offer_note: Optional[str] = None
    status: Optional[str] = None


@router.get("/debug")
def debug(user: user_dependency):
    require_admin(user)
    return schema_debug(engine)


@router.post("/import-zip")
async def import_zip(
    user: user_dependency,
    db: db_dependency,
    file: UploadFile = File(...),
    import_name: Optional[str] = Form(default=None),
):
    require_admin(user)

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload a ZIP file")

    tmp_dir = Path("tmp_flyer_offer_imports")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / file.filename

    with tmp_path.open("wb") as dst:
        shutil.copyfileobj(file.file, dst)

    try:
        return import_zip_to_draft(db, tmp_path, import_name=import_name or Path(file.filename).stem)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        try:
            tmp_path.unlink()
        except Exception:
            pass


@router.get("/flyers")
def list_flyers(user: user_dependency, db: db_dependency, limit: int = 50):
    require_admin(user)
    rows = db.execute(
        text("""
            SELECT f.*,
                   COUNT(o.id) AS offers_count,
                   SUM(CASE WHEN o.match_status LIKE 'auto_matched%' THEN 1 ELSE 0 END) AS auto_matched_count,
                   SUM(CASE WHEN o.match_status = 'needs_review' THEN 1 ELSE 0 END) AS needs_review_count,
                   SUM(CASE WHEN o.match_status = 'new_product_suggestion' THEN 1 ELSE 0 END) AS new_product_count,
                   SUM(CASE WHEN o.status = 'published' THEN 1 ELSE 0 END) AS published_count
            FROM flyers f
            LEFT JOIN flyer_offers o ON o.flyer_id = f.id
            GROUP BY f.id
            ORDER BY f.id DESC
            LIMIT :limit
        """),
        {"limit": limit},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.get("/flyers/{flyer_id}/offers")
def list_offers(
    user: user_dependency,
    db: db_dependency,
    flyer_id: int,
    match_status: Optional[str] = None,
    status_filter: Optional[str] = None,
):
    require_admin(user)

    where = ["o.flyer_id = :flyer_id"]
    params = {"flyer_id": flyer_id}
    if match_status:
        where.append("o.match_status = :match_status")
        params["match_status"] = match_status
    if status_filter:
        where.append("o.status = :status_filter")
        params["status_filter"] = status_filter

    sql = f"""
        SELECT o.*,
               p.name AS product_name,
               p.image AS product_image,
               sp.name AS suggested_product_name
        FROM flyer_offers o
        LEFT JOIN products p ON p.id = o.product_id
        LEFT JOIN products sp ON sp.id = o.suggested_product_id
        WHERE {' AND '.join(where)}
        ORDER BY o.match_status DESC, o.flyer_page ASC, o.id ASC
    """
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(row) for row in rows]


@router.get("/offers/{offer_id}/suggestions")
def suggestions(user: user_dependency, db: db_dependency, offer_id: int, limit: int = 8):
    require_admin(user)
    offer = db.execute(text("SELECT * FROM flyer_offers WHERE id=:id"), {"id": offer_id}).mappings().first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    # Simple SQL candidate search by pieces of words; admin can choose manually.
    words = [w for w in str(offer["normalized_name"] or "").split() if len(w) >= 4][:6]
    if not words:
        return []

    clauses = []
    params = {"limit": limit}
    for i, word in enumerate(words):
        key = f"w{i}"
        clauses.append(f"lower(p.name) LIKE :{key}")
        params[key] = f"%{word}%"

    rows = db.execute(
        text(f"""
            SELECT p.id, p.name, p.category, p.unit, p.image, p.original_price, p.discounted_price, s.name AS supermarket_name
            FROM products p
            LEFT JOIN supermarkets s ON s.id = p.supermarket_id
            WHERE {' OR '.join(clauses)}
            LIMIT :limit
        """),
        params,
    ).mappings().all()
    return [dict(row) for row in rows]


@router.put("/offers/{offer_id}")
def update_offer(user: user_dependency, db: db_dependency, offer_id: int, request: OfferPatch):
    require_admin(user)
    data = request.model_dump(exclude_unset=True)
    if not data:
        return {"ok": True}

    allowed = {
        "raw_name", "category", "unit", "offer_price", "original_price", "price_type", "price_unit",
        "flyer_page", "valid_from", "valid_to", "offer_note", "status",
    }
    fields = [field for field in data if field in allowed]
    if not fields:
        return {"ok": True}

    params = {"id": offer_id, **{field: data[field] for field in fields}}
    set_clause = ", ".join(f"{field}=:{field}" for field in fields)
    db.execute(text(f"UPDATE flyer_offers SET {set_clause} WHERE id=:id"), params)
    db.commit()
    return {"ok": True}


@router.post("/offers/{offer_id}/associate")
def associate(user: user_dependency, db: db_dependency, offer_id: int, request: AssociateRequest):
    require_admin(user)
    try:
        associate_offer(db, offer_id=offer_id, product_id=request.product_id, create_alias=request.create_alias)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}


@router.post("/offers/{offer_id}/create-product")
def create_product(user: user_dependency, db: db_dependency, offer_id: int):
    require_admin(user)
    try:
        product_id = create_product_from_offer(db, offer_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "product_id": product_id}


@router.post("/offers/{offer_id}/reject")
def reject(user: user_dependency, db: db_dependency, offer_id: int):
    require_admin(user)
    db.execute(text("UPDATE flyer_offers SET status='rejected' WHERE id=:id"), {"id": offer_id})
    db.commit()
    return {"ok": True}


@router.post("/flyers/{flyer_id}/approve-auto")
def approve_auto(user: user_dependency, db: db_dependency, flyer_id: int):
    require_admin(user)
    result = db.execute(
        text("""
            UPDATE flyer_offers
            SET status='approved'
            WHERE flyer_id=:fid
              AND product_id IS NOT NULL
              AND match_status LIKE 'auto_matched%'
              AND status='draft'
        """),
        {"fid": flyer_id},
    )
    db.commit()
    return {"ok": True, "approved": result.rowcount}


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
    ).scalar()
    if missing and int(missing) > 0:
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
    return {"ok": True, "published": result.rowcount}


@router.get("/products/search")
def product_search(user: user_dependency, db: db_dependency, q: str, limit: int = 20):
    require_admin(user)
    rows = db.execute(
        text("""
            SELECT p.id, p.name, p.category, p.unit, p.image, p.original_price, p.discounted_price, s.name AS supermarket_name
            FROM products p
            LEFT JOIN supermarkets s ON s.id = p.supermarket_id
            WHERE lower(p.name) LIKE lower(:q)
            ORDER BY p.name
            LIMIT :limit
        """),
        {"q": f"%{q}%", "limit": limit},
    ).mappings().all()
    return [dict(row) for row in rows]
