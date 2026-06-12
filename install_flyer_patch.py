from __future__ import annotations

import shutil
from pathlib import Path


PATCH_FILES = [
    "app/routers/flyer_catalog.py",
    "app/services/flyer_catalog_importer.py",
    "tools/flyers/capture_flyer_images.py",
    "tools/flyers/README.md",
    "docs/FLYER_CATALOG_IMPORT.md",
]


def copy_patch_files(project_root: Path, patch_root: Path) -> None:
    for rel in PATCH_FILES:
        src = patch_root / rel
        dst = project_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"OK copied {rel}")


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


def patch_main_py(project_root: Path) -> None:
    main_path = project_root / "app" / "main.py"
    if not main_path.exists():
        raise FileNotFoundError("Non trovo app/main.py. Esegui questo script dalla root del progetto.")

    backup_path = main_path.with_suffix(".py.bak_flyer_patch")
    if not backup_path.exists():
        shutil.copy2(main_path, backup_path)
        print(f"Backup creato: {backup_path}")

    text = main_path.read_text(encoding="utf-8")

    text = ensure_import(text, "from pathlib import Path")
    text = ensure_import(text, "from app.routers import flyer_catalog")

    if "from fastapi.staticfiles import StaticFiles" not in text:
        text = ensure_import(text, "from fastapi.staticfiles import StaticFiles")

    static_block = (
        'STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "static"\n'
        'if STATIC_DIR.exists():\n'
        '    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")\n'
        '\n'
    )

    if 'app.mount("/static"' not in text and "app = FastAPI()" in text:
        text = text.replace("app = FastAPI()\n", "app = FastAPI()\n\n" + static_block, 1)

    include_line = "app.include_router(flyer_catalog.router)"
    if include_line not in text:
        marker = "app.include_router(shopping_history.router)"
        if marker in text:
            text = text.replace(marker, marker + "\n" + include_line, 1)
        else:
            text = text.rstrip() + "\n" + include_line + "\n"

    main_path.write_text(text, encoding="utf-8")
    print("OK patched app/main.py")


def main() -> None:
    project_root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (project_root / "app").exists():
        raise RuntimeError("Non vedo la cartella app/. Devi lanciare: python install_flyer_patch.py dalla root del progetto.")

    copy_patch_files(project_root, patch_root)
    patch_main_py(project_root)

    (project_root / "frontend" / "static" / "images" / "products").mkdir(parents=True, exist_ok=True)
    (project_root / "imported_flyer_images").mkdir(parents=True, exist_ok=True)

    print()
    print("Patch installata.")
    print("Ora RIAVVIA uvicorn, poi apri http://127.0.0.1:8000/docs")
    print("Dovresti vedere: POST /flyer-catalog/import-zip")
    print("Dopo import ZIP, troverai anche le immagini in: imported_flyer_images/<import>/product_images/")


if __name__ == "__main__":
    main()
