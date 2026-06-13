from __future__ import annotations

import json
import re
import shutil
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from starlette import status

from app.routers.auth import get_current_user


router = APIRouter(prefix="/admin/flyer-extractor", tags=["admin-flyer-extractor"])

user_dependency = Annotated[dict, Depends(get_current_user)]

STATIC_ROOT = Path("static")
FLYER_ROOT = STATIC_ROOT / "flyer_pages"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class FlyerUrlRequest(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    supermarket_id: Optional[int] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


def require_admin(user: dict) -> None:
    if not user or user.get("user_role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


def now_stamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def safe_slug(value: str | None, fallback: str = "flyer") -> str:
    value = (value or fallback).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or fallback


def public_url(path: Path) -> str:
    normalized = path.as_posix()
    if normalized.startswith("static/"):
        return "/" + normalized
    return "/static/" + normalized


def extraction_dir(title: str | None) -> tuple[str, Path]:
    extraction_id = f"{now_stamp()}_{safe_slug(title)}_{uuid4().hex[:8]}"
    target = FLYER_ROOT / extraction_id
    target.mkdir(parents=True, exist_ok=True)
    return extraction_id, target


def write_manifest(target: Path, manifest: dict) -> None:
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def read_manifest(extraction_id: str) -> dict:
    path = FLYER_ROOT / extraction_id / "manifest.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Extraction not found")
    return json.loads(path.read_text(encoding="utf-8"))


def build_zip(target: Path, extraction_id: str) -> Path:
    zip_path = target / f"{extraction_id}_pages.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(target.iterdir()):
            if file.is_file() and file.name != zip_path.name:
                archive.write(file, file.name)
    return zip_path


def try_make_contact_sheet(target: Path, page_paths: list[Path], extraction_id: str) -> Optional[Path]:
    if not page_paths:
        return None

    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None

    thumbs = []
    for page_path in page_paths[:80]:
        try:
            img = Image.open(page_path).convert("RGB")
            img.thumbnail((220, 300))
            canvas = Image.new("RGB", (240, 335), "white")
            x = (240 - img.width) // 2
            canvas.paste(img, (x, 10))
            draw = ImageDraw.Draw(canvas)
            draw.text((12, 310), page_path.stem.replace("_", " "), fill=(15, 23, 42))
            thumbs.append(canvas)
        except Exception:
            continue

    if not thumbs:
        return None

    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 240, rows * 335), "white")
    for idx, thumb in enumerate(thumbs):
        x = (idx % cols) * 240
        y = (idx // cols) * 335
        sheet.paste(thumb, (x, y))

    out = target / f"{extraction_id}_contact_sheet.jpg"
    sheet.save(out, "JPEG", quality=90)
    return out


def render_pdf_to_images(pdf_bytes: bytes, target: Path, scale: float = 2.0) -> list[Path]:
    try:
        import fitz  # PyMuPDF
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="PyMuPDF is missing. Add PyMuPDF to requirements.txt, redeploy, then retry.",
        )

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid PDF file: {exc}")

    page_paths: list[Path] = []
    matrix = fitz.Matrix(scale, scale)

    for index, page in enumerate(document, start=1):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        out = target / f"page_{index:03d}.jpg"
        pix.save(out)
        page_paths.append(out)

    document.close()
    return page_paths


def extract_images_zip(zip_bytes: bytes, target: Path) -> list[Path]:
    tmp_zip = target / "source_images.zip"
    tmp_zip.write_bytes(zip_bytes)

    page_paths: list[Path] = []
    with zipfile.ZipFile(tmp_zip, "r") as archive:
        members = [
            member for member in archive.namelist()
            if not member.endswith("/")
            and Path(member).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS
            and "__MACOSX" not in member
        ]

        if not members:
            raise HTTPException(status_code=400, detail="ZIP does not contain JPG/PNG/WEBP page images.")

        members = sorted(members)
        for index, member in enumerate(members, start=1):
            ext = Path(member).suffix.lower()
            out = target / f"page_{index:03d}{ext}"
            with archive.open(member) as source, out.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            page_paths.append(out)

    return page_paths


def save_single_image(image_bytes: bytes, target: Path, extension: str = ".jpg") -> list[Path]:
    if extension.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        extension = ".jpg"
    out = target / f"page_001{extension.lower()}"
    out.write_bytes(image_bytes)
    return [out]


def make_manifest(
    *,
    extraction_id: str,
    target: Path,
    title: str | None,
    supermarket_id: int | None,
    valid_from: str | None,
    valid_to: str | None,
    source_type: str,
    source_name: str | None,
    page_paths: list[Path],
) -> dict:
    contact_sheet = try_make_contact_sheet(target, page_paths, extraction_id)
    zip_path = build_zip(target, extraction_id)

    manifest = {
        "extraction_id": extraction_id,
        "title": title or extraction_id,
        "supermarket_id": supermarket_id,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "source_type": source_type,
        "source_name": source_name,
        "pages_count": len(page_paths),
        "created_at": datetime.utcnow().isoformat(),
        "pages": [
            {
                "page_number": index,
                "filename": path.name,
                "image_url": public_url(path),
            }
            for index, path in enumerate(page_paths, start=1)
        ],
        "contact_sheet_url": public_url(contact_sheet) if contact_sheet else None,
        "zip_url": f"/admin/flyer-extractor/{extraction_id}/zip",
        "manifest_url": f"/admin/flyer-extractor/{extraction_id}/manifest",
        "notes": [
            "No OCR is performed here.",
            "This extractor only creates page images for manual/ChatGPT-assisted reading.",
        ],
    }
    write_manifest(target, manifest)
    return manifest


@router.get("/health")
def health(user: user_dependency):
    require_admin(user)
    fitz_available = True
    pillow_available = True

    try:
        import fitz  # noqa
    except Exception:
        fitz_available = False

    try:
        import PIL  # noqa
    except Exception:
        pillow_available = False

    return {
        "ok": True,
        "no_ocr": True,
        "storage_dir": str(FLYER_ROOT),
        "pymupdf_available": fitz_available,
        "pillow_available": pillow_available,
        "supported_inputs": ["pdf_upload", "images_zip_upload", "direct_pdf_url", "direct_image_url"],
    }


@router.get("/recent")
def recent(user: user_dependency, limit: int = 20):
    require_admin(user)
    FLYER_ROOT.mkdir(parents=True, exist_ok=True)

    rows = []
    for manifest_path in sorted(FLYER_ROOT.glob("*/manifest.json"), reverse=True)[:limit]:
        try:
            rows.append(json.loads(manifest_path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return rows


@router.post("/pdf")
async def upload_pdf(
    user: user_dependency,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    supermarket_id: Optional[int] = Form(default=None),
    valid_from: Optional[str] = Form(default=None),
    valid_to: Optional[str] = Form(default=None),
):
    require_admin(user)

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload a PDF file.")

    extraction_id, target = extraction_dir(title or Path(file.filename).stem)
    pdf_bytes = await file.read()
    (target / "source.pdf").write_bytes(pdf_bytes)

    page_paths = render_pdf_to_images(pdf_bytes, target)
    return make_manifest(
        extraction_id=extraction_id,
        target=target,
        title=title or Path(file.filename).stem,
        supermarket_id=supermarket_id,
        valid_from=valid_from,
        valid_to=valid_to,
        source_type="pdf_upload",
        source_name=file.filename,
        page_paths=page_paths,
    )


@router.post("/images-zip")
async def upload_images_zip(
    user: user_dependency,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    supermarket_id: Optional[int] = Form(default=None),
    valid_from: Optional[str] = Form(default=None),
    valid_to: Optional[str] = Form(default=None),
):
    require_admin(user)

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload a ZIP containing page images.")

    extraction_id, target = extraction_dir(title or Path(file.filename).stem)
    zip_bytes = await file.read()
    page_paths = extract_images_zip(zip_bytes, target)

    return make_manifest(
        extraction_id=extraction_id,
        target=target,
        title=title or Path(file.filename).stem,
        supermarket_id=supermarket_id,
        valid_from=valid_from,
        valid_to=valid_to,
        source_type="images_zip_upload",
        source_name=file.filename,
        page_paths=page_paths,
    )


@router.post("/url")
def import_direct_url(user: user_dependency, request: FlyerUrlRequest):
    require_admin(user)

    url = str(request.url)
    extraction_id, target = extraction_dir(request.title or "url-flyer")

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            content_type = response.headers.get("content-type", "").lower()
            body = response.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not download URL: {exc}")

    lower_url = url.lower().split("?")[0]
    if "pdf" in content_type or lower_url.endswith(".pdf"):
        (target / "source.pdf").write_bytes(body)
        page_paths = render_pdf_to_images(body, target)
        source_type = "direct_pdf_url"
    elif any(lower_url.endswith(ext) for ext in ALLOWED_IMAGE_EXTENSIONS) or content_type.startswith("image/"):
        ext = Path(lower_url).suffix if Path(lower_url).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS else ".jpg"
        page_paths = save_single_image(body, target, ext)
        source_type = "direct_image_url"
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                "This URL is not a direct PDF/image. No OCR/crawling is performed. "
                "For website flyers, generate a ZIP of page images and upload it with /images-zip."
            ),
        )

    return make_manifest(
        extraction_id=extraction_id,
        target=target,
        title=request.title,
        supermarket_id=request.supermarket_id,
        valid_from=request.valid_from,
        valid_to=request.valid_to,
        source_type=source_type,
        source_name=url,
        page_paths=page_paths,
    )


@router.get("/{extraction_id}/manifest")
def get_manifest(user: user_dependency, extraction_id: str):
    require_admin(user)
    return read_manifest(extraction_id)


@router.get("/{extraction_id}/zip")
def download_zip(user: user_dependency, extraction_id: str):
    require_admin(user)
    target = FLYER_ROOT / extraction_id
    if not target.exists():
        raise HTTPException(status_code=404, detail="Extraction not found")

    zip_path = target / f"{extraction_id}_pages.zip"
    if not zip_path.exists():
        build_zip(target, extraction_id)

    return FileResponse(
        path=zip_path,
        filename=zip_path.name,
        media_type="application/zip",
    )


@router.delete("/{extraction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_extraction(user: user_dependency, extraction_id: str):
    require_admin(user)
    target = FLYER_ROOT / extraction_id
    if not target.exists():
        raise HTTPException(status_code=404, detail="Extraction not found")
    shutil.rmtree(target)
