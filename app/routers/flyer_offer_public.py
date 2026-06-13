from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.services.flyer_offer_schema import ensure_flyer_offer_schema


router = APIRouter(prefix="/flyer-offers", tags=["flyer-offers"])


@router.get("/active")
def active_offers(supermarket_id: Optional[int] = None, limit: int = 500):
    ensure_flyer_offer_schema(engine)
    db = SessionLocal()
    try:
        where = ["o.status = 'published'"]
        params = {"limit": limit}
        if supermarket_id is not None:
            where.append("f.supermarket_id = :sid")
            params["sid"] = supermarket_id

        rows = db.execute(
            text(f"""
                SELECT o.*, f.retailer, f.title AS flyer_title, f.supermarket_id,
                       p.name AS product_name, p.image AS product_image, p.category AS product_category
                FROM flyer_offers o
                JOIN flyers f ON f.id = o.flyer_id
                LEFT JOIN products p ON p.id = o.product_id
                WHERE {' AND '.join(where)}
                ORDER BY o.valid_to DESC, o.flyer_page ASC, o.id ASC
                LIMIT :limit
            """),
            params,
        ).mappings().all()
        return [dict(row) for row in rows]
    finally:
        db.close()


@router.get("/product/{product_id}")
def active_offer_for_product(product_id: int):
    ensure_flyer_offer_schema(engine)
    db = SessionLocal()
    try:
        row = db.execute(
            text("""
                SELECT o.*, f.retailer, f.title AS flyer_title, f.supermarket_id
                FROM flyer_offers o
                JOIN flyers f ON f.id = o.flyer_id
                WHERE o.status = 'published'
                  AND o.product_id = :pid
                ORDER BY o.valid_to DESC, o.id DESC
                LIMIT 1
            """),
            {"pid": product_id},
        ).mappings().first()
        return dict(row) if row else None
    finally:
        db.close()
