from __future__ import annotations
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.routers.auth import get_current_user
from app.services.flyer_offer_bulk_images_v26e import (
    associate_offer_v26e,
    bulk_approve_offers_v26e,
    bulk_associate_suggested_v26e,
    bulk_create_products_v26e,
    bulk_reject_offers_v26e,
    create_product_from_offer_v26e,
    repair_product_images_from_offers_v26e,
)

router = APIRouter(prefix="/admin/flyer-offers/v26e", tags=["admin-flyer-offers-v26e"])
user_dependency = Annotated[dict, Depends(get_current_user)]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

def require_admin(user: dict) -> None:
    if not user or user.get("user_role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

class AssociateRequest(BaseModel):
    product_id: int
    create_alias: bool = True

class BulkRequest(BaseModel):
    offer_ids: list[int]
    create_alias: bool = True

class RepairImagesRequest(BaseModel):
    flyer_id: Optional[int] = None

@router.post("/offers/{offer_id}/associate")
def associate(user: user_dependency, db: db_dependency, offer_id: int, request: AssociateRequest):
    require_admin(user)
    try:
        associate_offer_v26e(db, offer_id=offer_id, product_id=request.product_id, create_alias=request.create_alias)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/offers/{offer_id}/create-product")
def create_product(user: user_dependency, db: db_dependency, offer_id: int):
    require_admin(user)
    try:
        return {"ok": True, "product_id": create_product_from_offer_v26e(db, offer_id)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/offers/bulk-associate-suggested")
def bulk_associate(user: user_dependency, db: db_dependency, request: BulkRequest):
    require_admin(user)
    return {"ok": True, **bulk_associate_suggested_v26e(db, request.offer_ids, create_alias=request.create_alias)}

@router.post("/offers/bulk-create-products")
def bulk_create(user: user_dependency, db: db_dependency, request: BulkRequest):
    require_admin(user)
    return {"ok": True, **bulk_create_products_v26e(db, request.offer_ids)}

@router.post("/offers/bulk-approve")
def bulk_approve(user: user_dependency, db: db_dependency, request: BulkRequest):
    require_admin(user)
    return {"ok": True, **bulk_approve_offers_v26e(db, request.offer_ids)}

@router.post("/offers/bulk-reject")
def bulk_reject(user: user_dependency, db: db_dependency, request: BulkRequest):
    require_admin(user)
    return {"ok": True, **bulk_reject_offers_v26e(db, request.offer_ids)}

@router.post("/repair-product-images")
def repair_images(user: user_dependency, db: db_dependency, request: RepairImagesRequest):
    require_admin(user)
    return {"ok": True, **repair_product_images_from_offers_v26e(db, flyer_id=request.flyer_id)}
