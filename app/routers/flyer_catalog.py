from __future__ import annotations

import json
import re
import shutil
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from starlette import status

from app.database import SessionLocal
from app.routers.auth import get_current_user
from app.services.flyer_catalog_importer import import_flyer_catalog


router = APIRouter(
    prefix="/flyer-catalog",
    tags=["flyer-catalog"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_IMAGES_DIR = PROJECT_ROOT / "frontend" / "static" / "images" / "products"
STATIC_PRODUCT_PREFIX = "/static/images/products"

# Extra folder for the user: this is independent from frontend/static.
# After an import you can open this folder on your computer and see all imported images.
IMPORTED_FLYER_IMAGES_DIR = PROJECT_ROOT / "imported_flyer_images"

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class FlyerProductImportItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    product_name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[str] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    old_price: Optional[float] = None
    original_price: Optional[float] = None
    discounted_price: Optional[float] = None
    image_path: Optional[str] = None
    image: Optional[str] = None
    image_url: Optional[str] = None
    page: Optional[int] = None
    aisle_order: Optional[float] = None


class FlyerCatalogImportRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    retailer: str = Field(min_length=1, max_length=100)
    default_category: Optional[str] = None
    products: list[FlyerProductImportItem] = Field(default_factory=list)


def slugify(value: str, max_length: int = 90) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9àèéìòù]+", "-", value, flags=re.I)
    value = re.sub(r"-+", "-", value).strip("-")
    return (value or "product")[:max_length].strip("-") or "product"


def unique_path(directory: Path, filename: str) -> Path:
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    candidate = directory / filename
    counter = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def find_products_json(zip_file: zipfile.ZipFile) -> str:
    candidates = [
        name for name in zip_file.namelist()
        if Path(name).name.lower() == "products.json" and not name.endswith("/")
    ]
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ZIP must contain a products.json file",
        )
    return candidates[0]


def build_zip_image_lookup(zip_file: zipfile.ZipFile) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for name in zip_file.namelist():
        if name.endswith("/"):
            continue
        suffix = Path(name).suffix.lower()
        if suffix not in ALLOWED_IMAGE_EXTENSIONS:
            continue
        normalized = name.replace("\\", "/")
        lookup[normalized] = name
        lookup[Path(normalized).name] = name
    return lookup


def create_import_folder_name(filename: str | None, payload: dict[str, Any]) -> str:
    retailer = payload.get("retailer") or payload.get("supermarket") or payload.get("store") or "flyer"
    valid_from = payload.get("valid_from") or payload.get("from") or ""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    base_name = Path(filename or "flyer_import.zip").stem
    label = "_".join(part for part in [str(retailer), str(valid_from), base_name, timestamp] if part)
    return slugify(label, max_length=140)


def save_image_from_zip(
    zip_file: zipfile.ZipFile,
    member_name: str,
    product_name: str,
    *,
    archive_images_dir: Path | None = None,
    saved_images: list[dict[str, str]] | None = None,
) -> str | None:
    suffix = Path(member_name).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        return None

    PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = f"{slugify(product_name)}{suffix}"
    target_path = unique_path(PRODUCT_IMAGES_DIR, safe_name)

    with zip_file.open(member_name) as source, target_path.open("wb") as target:
        target.write(source.read())

    archive_path_str = ""
    if archive_images_dir is not None:
        archive_images_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_images_dir / target_path.name
        shutil.copy2(target_path, archive_path)
        archive_path_str = str(archive_path)

    static_url = f"{STATIC_PRODUCT_PREFIX}/{target_path.name}"

    if saved_images is not None:
        saved_images.append({
            "product_name": product_name,
            "frontend_path": str(target_path),
            "frontend_url": static_url,
            "archive_path": archive_path_str,
        })

    return static_url


@router.post("/import-json", status_code=status.HTTP_201_CREATED)
async def import_flyer_catalog_json(
    user: user_dependency,
    db: db_dependency,
    request: FlyerCatalogImportRequest,
    update_existing: bool = True,
):
    """
    Imports catalog products from a structured flyer JSON.

    This endpoint does not upload image files. Use `image` or `image_url` only when
    the image path is already reachable by the frontend, or use `/import-zip`.
    """
    try:
        return import_flyer_catalog(
            db,
            request.model_dump(),
            update_existing=update_existing,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/import-zip", status_code=status.HTTP_201_CREATED)
async def import_flyer_catalog_zip(
    user: user_dependency,
    db: db_dependency,
    file: UploadFile = File(...),
    update_existing: bool = Form(True),
    save_archive_folder: bool = Form(True),
):
    """
    Imports products and product images from a ZIP package.

    Expected ZIP structure:

    - products.json
    - product_images/*.jpg

    What happens to images:
    1. They are copied to `frontend/static/images/products/`, so the frontend can display them.
    2. If `save_archive_folder=true`, they are also copied to:
       `imported_flyer_images/<import_name>/product_images/`
       so you can easily browse the imported images on your computer.
    """
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload a .zip file")

    raw = await file.read()

    try:
        zip_file = zipfile.ZipFile(BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ZIP file") from exc

    with zip_file:
        products_json_name = find_products_json(zip_file)
        try:
            payload: dict[str, Any] = json.loads(zip_file.read(products_json_name).decode("utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid products.json") from exc

        image_lookup = build_zip_image_lookup(zip_file)

        import_folder = None
        archive_images_dir = None
        if save_archive_folder:
            import_folder = IMPORTED_FLYER_IMAGES_DIR / create_import_folder_name(file.filename, payload)
            archive_images_dir = import_folder / "product_images"
            archive_images_dir.mkdir(parents=True, exist_ok=True)

            # Store a copy of products.json next to the images for easy inspection.
            import_folder.mkdir(parents=True, exist_ok=True)
            (import_folder / "products.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        saved_images: list[dict[str, str]] = []

        def image_resolver(item: dict[str, Any], product_name: str) -> str | None:
            requested = item.get("image_path") or item.get("image") or item.get("image_url")
            if not requested:
                return None

            requested_str = str(requested).replace("\\", "/")
            # External/already served images are kept as-is.
            if requested_str.startswith("http://") or requested_str.startswith("https://") or requested_str.startswith("/static/"):
                return requested_str

            member = image_lookup.get(requested_str) or image_lookup.get(Path(requested_str).name)
            if not member:
                return None

            return save_image_from_zip(
                zip_file,
                member,
                product_name,
                archive_images_dir=archive_images_dir,
                saved_images=saved_images,
            )

        try:
            result = import_flyer_catalog(
                db,
                payload,
                image_resolver=image_resolver,
                update_existing=update_existing,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        result["image_archive_folder"] = str(import_folder) if import_folder else None
        result["image_archive_product_images_folder"] = str(archive_images_dir) if archive_images_dir else None
        result["images_saved_count"] = len(saved_images)
        result["images_saved"] = saved_images[:50]
        result["images_saved_note"] = "Only first 50 image records are returned in the API response." if len(saved_images) > 50 else None

        return result
