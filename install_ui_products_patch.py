from __future__ import annotations

import re
import shutil
from pathlib import Path

PATCH_FILES = [
    "frontend/products.html",
    "frontend/css/products.css",
    "frontend/css/modal.css",
    "frontend/js/products.js",
    "frontend/js/modal-function.js",
    "frontend/js/modal-loader.js",
    "app/routers/products.py",
    "app/routers/flyer_catalog.py",
    "app/services/flyer_catalog_importer.py",
    "app/services/schema_compat.py",
    "tools/flyers/capture_flyer_images.py",
    "tools/flyers/README.md",
    "docs/PRODUCTS_DESKTOP_REDESIGN.md",
]

PRODUCT_MODEL_FIELDS = """
    # Metadata importati dai volantini/cataloghi.
    brand = Column(String, nullable=True)
    flyer_page = Column(Integer, nullable=True)
    flyer_valid_from = Column(String, nullable=True)
    flyer_valid_to = Column(String, nullable=True)
    flyer_source = Column(String, nullable=True)
    flyer_source_url = Column(String, nullable=True)
    is_lidl_plus = Column(Boolean, default=False)
    flyer_imported_at = Column(String, nullable=True)
    offer_note = Column(String, nullable=True)
    discount_percent = Column(Float, nullable=True)
""".rstrip()


def copy_patch_files(project_root: Path, patch_root: Path) -> None:
    for rel in PATCH_FILES:
        src = patch_root / rel
        dst = project_root / rel
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"OK copied {rel}")


def backup_once(path: Path, suffix: str) -> None:
    backup = path.with_suffix(path.suffix + suffix)
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)
        print(f"Backup creato: {backup}")


def ensure_import(text: str, import_line: str) -> str:
    if import_line in text:
        return text
    lines = text.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("from ") or line.startswith("import "):
            insert_at = i + 1
    lines.insert(insert_at, import_line)
    return "\n".join(lines) + "\n"


def patch_models(project_root: Path) -> None:
    path = project_root / "app" / "models.py"
    if not path.exists():
        raise FileNotFoundError("Non trovo app/models.py")
    backup_once(path, ".bak_products_ui_patch")

    text = path.read_text(encoding="utf-8")
    if "flyer_page = Column" in text:
        print("OK app/models.py già contiene flyer_page")
        return

    marker = "    location = Column(String, nullable=True)"
    if marker not in text:
        raise RuntimeError("Non riesco a trovare il punto in Products dove aggiungere i campi flyer.")

    text = text.replace(marker, marker + "\n" + PRODUCT_MODEL_FIELDS, 1)
    path.write_text(text, encoding="utf-8")
    print("OK patched app/models.py")


def patch_main(project_root: Path) -> None:
    path = project_root / "app" / "main.py"
    if not path.exists():
        raise FileNotFoundError("Non trovo app/main.py")
    backup_once(path, ".bak_products_ui_patch")

    text = path.read_text(encoding="utf-8")
    text = ensure_import(text, "from pathlib import Path")
    text = ensure_import(text, "from app.routers import flyer_catalog")
    text = ensure_import(text, "from app.services.schema_compat import ensure_product_metadata_columns")

    if "from fastapi.staticfiles import StaticFiles" not in text:
        text = ensure_import(text, "from fastapi.staticfiles import StaticFiles")

    static_block = (
        'STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "static"\n'
        'if STATIC_DIR.exists() and not any(getattr(route, "path", None) == "/static" for route in app.routes):\n'
        '    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")\n'
        '\n'
    )

    if 'app.mount("/static"' not in text and "app = FastAPI()" in text:
        text = text.replace("app = FastAPI()\n", "app = FastAPI()\n\n" + static_block, 1)

    if "ensure_product_metadata_columns(engine)" not in text:
        marker = "Base.metadata.create_all(bind=engine)"
        if marker in text:
            text = text.replace(marker, marker + "\nensure_product_metadata_columns(engine)", 1)
        else:
            text += "\nBase.metadata.create_all(bind=engine)\nensure_product_metadata_columns(engine)\n"

    include_line = "app.include_router(flyer_catalog.router)"
    if include_line not in text:
        # Put it near the other routers when possible.
        matches = list(re.finditer(r"app\.include_router\([^\n]+\)", text))
        if matches:
            last = matches[-1]
            text = text[:last.end()] + "\n" + include_line + text[last.end():]
        else:
            text = text.rstrip() + "\n" + include_line + "\n"

    path.write_text(text, encoding="utf-8")
    print("OK patched app/main.py")


def main() -> None:
    project_root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (project_root / "app").exists() or not (project_root / "frontend").exists():
        raise RuntimeError("Devi lanciare questo script dalla root del progetto, dove vedi app/ e frontend/.")

    copy_patch_files(project_root, patch_root)
    patch_models(project_root)
    patch_main(project_root)

    (project_root / "frontend" / "static" / "images" / "products").mkdir(parents=True, exist_ok=True)
    (project_root / "imported_flyer_images").mkdir(parents=True, exist_ok=True)

    print("\nPatch grafica installata.")
    print("Riavvia uvicorn e poi ricarica products.html con cache svuotata / Ctrl+F5.")


if __name__ == "__main__":
    main()
