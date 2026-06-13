from __future__ import annotations

import json
import re
import shutil
import unicodedata
import zipfile
from pathlib import Path
from typing import Annotated, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.routers.auth import get_current_user
from app.services.flyer_offer_schema import ensure_flyer_offer_schema
from app.database import engine


router = APIRouter(prefix="/admin/flyer-offer-images", tags=["admin-flyer-offer-images"])


def get_db():
    ensure_flyer_offer_schema(engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


PRODUCT_IMAGE_PREFIX = "/static/images/products/"


def require_admin(user: dict) -> None:
    if not user or user.get("user_role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


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


def read_products_payload(z: zipfile.ZipFile) -> list[dict[str, Any]]:
    if "products.json" not in z.namelist():
        raise HTTPException(status_code=400, detail="ZIP must contain products.json")

    payload = json.loads(z.read("products.json").decode("utf-8"))
    if isinstance(payload, list):
        products = payload
    elif isinstance(payload, dict):
        products = payload.get("products") or payload.get("offers") or []
    else:
        products = []

    return [item for item in products if isinstance(item, dict)]


def product_image_member(item: dict[str, Any]) -> str | None:
    for key in ["image_path", "image", "image_url"]:
        value = item.get(key)
        if value:
            return str(value).lstrip("/")
    return None


def build_product_maps(products: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for item in products:
        name = item.get("name") or item.get("raw_name") or item.get("product_name")
        norm = normalize_text(str(name or ""))
        if norm and norm not in by_name:
            by_name[norm] = item
    return by_name


def resolve_zip_member(z: zipfile.ZipFile, member: str | None) -> str | None:
    if not member:
        return None
    member = member.lstrip("/")
    names = set(z.namelist())

    if member in names:
        return member

    alt = f"product_images/{Path(member).name}"
    if alt in names:
        return alt

    # last fallback: find by filename
    filename = Path(member).name
    for name in names:
        if Path(name).name == filename:
            return name

    return None


def copy_zip_image_to_product_path(z: zipfile.ZipFile, item: dict[str, Any], product_name: str) -> str | None:
    member = resolve_zip_member(z, product_image_member(item))
    if not member:
        return None

    suffix = Path(member).suffix.lower() or ".jpg"
    filename = f"{slugify(product_name)}{suffix}"

    backend_dir = Path("static") / "images" / "products"
    frontend_dir = Path("frontend") / "static" / "images" / "products"
    backend_dir.mkdir(parents=True, exist_ok=True)
    frontend_dir.mkdir(parents=True, exist_ok=True)

    backend_dest = backend_dir / filename
    frontend_dest = frontend_dir / filename

    with z.open(member, "r") as src, backend_dest.open("wb") as dst:
        shutil.copyfileobj(src, dst)

    try:
        shutil.copy2(backend_dest, frontend_dest)
    except Exception:
        pass

    return f"{PRODUCT_IMAGE_PREFIX}{filename}"


def update_product_image(db: Session, product_id: int, new_image: str) -> None:
    db.execute(
        text("UPDATE products SET image=:image WHERE id=:id"),
        {"image": new_image, "id": product_id},
    )


def repair_linked_offer_products(
    db: Session,
    z: zipfile.ZipFile,
    product_map: dict[str, dict[str, Any]],
    flyer_id: int | None,
    force: bool,
) -> dict[str, int]:
    where = ["o.product_id IS NOT NULL"]
    params: dict[str, Any] = {}
    if flyer_id:
        where.append("o.flyer_id = :flyer_id")
        params["flyer_id"] = flyer_id

    rows = db.execute(
        text(f"""
            SELECT o.id AS offer_id, o.raw_name, o.product_id,
                   p.name AS product_name, p.image AS product_image
            FROM flyer_offers o
            JOIN products p ON p.id = o.product_id
            WHERE {' AND '.join(where)}
        """),
        params,
    ).mappings().all()

    checked = 0
    repaired = 0
    already_ok = 0
    not_found_in_zip = 0
    missing_zip_image = 0

    for row in rows:
        checked += 1
        current = str(row["product_image"] or "")

        if current.startswith(PRODUCT_IMAGE_PREFIX) and not force:
            already_ok += 1
            continue

        item = product_map.get(normalize_text(row["raw_name"])) or product_map.get(normalize_text(row["product_name"]))
        if not item:
            not_found_in_zip += 1
            continue

        new_image = copy_zip_image_to_product_path(z, item, row["product_name"] or row["raw_name"])
        if not new_image:
            missing_zip_image += 1
            continue

        update_product_image(db, int(row["product_id"]), new_image)
        repaired += 1

    return {
        "linked_checked": checked,
        "linked_repaired": repaired,
        "linked_already_ok": already_ok,
        "linked_not_found_in_zip": not_found_in_zip,
        "linked_missing_zip_image": missing_zip_image,
    }


def repair_loose_flyer_products(
    db: Session,
    z: zipfile.ZipFile,
    product_map: dict[str, dict[str, Any]],
    force: bool,
) -> dict[str, int]:
    """
    Also repairs products created directly from flyers even if they are not linked
    to flyer_offers anymore.
    """
    rows = db.execute(
        text("""
            SELECT p.id, p.name, p.image, p.flyer_valid_from, p.flyer_valid_to, p.flyer_source
            FROM products p
            LEFT JOIN supermarkets s ON s.id = p.supermarket_id
            WHERE lower(COALESCE(s.name, '')) LIKE '%conad%'
              AND (
                    COALESCE(p.image, '') LIKE '%flyer_offers%'
                 OR COALESCE(p.image, '') LIKE '%placeholder%'
                 OR COALESCE(p.image, '') LIKE 'http%'
                 OR p.flyer_valid_from = '2026-06-15'
                 OR p.flyer_valid_to = '2026-06-27'
                 OR lower(COALESCE(p.flyer_source, '')) LIKE '%conad%'
              )
        """)
    ).mappings().all()

    checked = 0
    repaired = 0
    already_ok = 0
    not_found_in_zip = 0
    missing_zip_image = 0

    for row in rows:
        checked += 1
        current = str(row["image"] or "")
        if current.startswith(PRODUCT_IMAGE_PREFIX) and not force:
            already_ok += 1
            continue

        item = product_map.get(normalize_text(row["name"]))
        if not item:
            not_found_in_zip += 1
            continue

        new_image = copy_zip_image_to_product_path(z, item, row["name"])
        if not new_image:
            missing_zip_image += 1
            continue

        update_product_image(db, int(row["id"]), new_image)
        repaired += 1

    return {
        "loose_checked": checked,
        "loose_repaired": repaired,
        "loose_already_ok": already_ok,
        "loose_not_found_in_zip": not_found_in_zip,
        "loose_missing_zip_image": missing_zip_image,
    }


@router.post("/repair-from-zip")
async def repair_from_zip(
    user: user_dependency,
    db: db_dependency,
    file: UploadFile = File(...),
    flyer_id: Optional[int] = Form(default=None),
    force: bool = Form(default=True),
):
    require_admin(user)

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload the same flyer import ZIP")

    tmp_dir = Path("tmp_flyer_image_repairs")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{uuid4().hex}_{file.filename}"

    with tmp_path.open("wb") as dst:
        shutil.copyfileobj(file.file, dst)

    try:
        with zipfile.ZipFile(tmp_path, "r") as z:
            products = read_products_payload(z)
            product_map = build_product_maps(products)

            linked = repair_linked_offer_products(db, z, product_map, flyer_id, force)
            loose = repair_loose_flyer_products(db, z, product_map, force)

            db.commit()

            return {
                "ok": True,
                "filename": file.filename,
                "zip_products": len(products),
                "flyer_id": flyer_id,
                "force": force,
                **linked,
                **loose,
                "total_repaired": linked["linked_repaired"] + loose["loose_repaired"],
            }
    except zipfile.BadZipFile:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        try:
            tmp_path.unlink()
        except Exception:
            pass
