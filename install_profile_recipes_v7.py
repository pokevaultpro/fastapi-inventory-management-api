from __future__ import annotations

import shutil
from pathlib import Path

PATCH_FILES = [
    "app/routers/profile.py",
    "app/routers/recipe_smart.py",
    "app/routers/products.py",
    "app/routers/cart.py",
    "app/routers/shopping_history.py",
    "app/routers/flyer_catalog.py",
    "app/services/schema_compat.py",
    "app/services/flyer_catalog_importer.py",
    "frontend/profile.html",
    "frontend/recipes.html",
    "frontend/css/profile.css",
    "frontend/css/recipes.css",
    "frontend/css/dashboard.css",
    "frontend/css/bottom-bar.css",
    "frontend/js/profile.js",
    "frontend/js/recipes.js",
    "frontend/js/dashboard.js",
    "frontend/js/quick-actions.js",
    "frontend/js/navbar.js",
    "docs/PROFILE_RECIPES_V7.md",
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
        raise FileNotFoundError("Non trovo app/main.py. Esegui dalla root del progetto.")
    backup = main_path.with_suffix(".py.bak_profile_recipes_v7")
    if not backup.exists():
        shutil.copy2(main_path, backup)
        print(f"Backup creato: {backup}")
    text = main_path.read_text(encoding="utf-8")
    text = ensure_import(text, "from pathlib import Path")
    text = ensure_import(text, "from fastapi.staticfiles import StaticFiles")
    text = ensure_import(text, "from app.routers import profile, recipe_smart, flyer_catalog")
    text = ensure_import(text, "from app.services.schema_compat import ensure_schema_compat")

    static_block = (
        'STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "static"\n'
        'if STATIC_DIR.exists() and not any(getattr(route, "path", None) == "/static" for route in app.routes):\n'
        '    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")\n\n'
    )
    if 'app.mount("/static"' not in text and "app = FastAPI()" in text:
        text = text.replace("app = FastAPI()\n", "app = FastAPI()\n\n" + static_block, 1)

    compat_block = (
        "\ntry:\n"
        "    ensure_schema_compat(engine)\n"
        "except Exception as exc:\n"
        "    print(f'Schema compatibility warning: {exc}')\n"
    )
    if "ensure_schema_compat(engine)" not in text:
        if "Base.metadata.create_all(bind=engine)" in text:
            text = text.replace("Base.metadata.create_all(bind=engine)", "Base.metadata.create_all(bind=engine)" + compat_block, 1)
        else:
            text += "\nBase.metadata.create_all(bind=engine)" + compat_block + "\n"

    for line in [
        "app.include_router(profile.router)",
        "app.include_router(recipe_smart.router)",
        "app.include_router(flyer_catalog.router)",
    ]:
        if line not in text:
            text = text.rstrip() + "\n" + line + "\n"
    main_path.write_text(text, encoding="utf-8")
    print("OK patched app/main.py")


def insert_after(text: str, anchor: str, addition: str) -> str:
    if addition.strip().splitlines()[0].strip() in text:
        return text
    if anchor not in text:
        return text
    return text.replace(anchor, anchor + "\n" + addition, 1)


def patch_models_py(project_root: Path) -> None:
    models_path = project_root / "app" / "models.py"
    if not models_path.exists():
        raise FileNotFoundError("Non trovo app/models.py")
    backup = models_path.with_suffix(".py.bak_profile_recipes_v7")
    if not backup.exists():
        shutil.copy2(models_path, backup)
        print(f"Backup creato: {backup}")
    text = models_path.read_text(encoding="utf-8")
    if "Text" not in text.splitlines()[0:5]:
        text = text.replace(
            "from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey",
            "from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text",
        )

    product_fields = """    brand = Column(String, nullable=True)
    flyer_page = Column(Integer, nullable=True)
    flyer_valid_from = Column(String, nullable=True)
    flyer_valid_to = Column(String, nullable=True)
    flyer_source = Column(String, nullable=True)
    flyer_source_url = Column(Text, nullable=True)
    is_lidl_plus = Column(Boolean, default=False)
    flyer_imported_at = Column(String, nullable=True)
    offer_note = Column(Text, nullable=True)
    discount_percent = Column(Float, nullable=True)"""
    if "flyer_valid_from = Column" not in text:
        text = insert_after(text, "    location = Column(String, nullable=True)", product_fields)

    recipe_fields = """    description = Column(Text, nullable=True)
    servings = Column(Integer, default=1)
    prep_time_minutes = Column(Integer, nullable=True)
    instructions = Column(Text, nullable=True)
    source_type = Column(String, default="personal")
    source_url = Column(Text, nullable=True)
    estimated_total = Column(Float, nullable=True)
    created_at = Column(String, nullable=True)"""
    if "prep_time_minutes = Column" not in text:
        text = insert_after(text, "    image = Column(String, nullable=True)", recipe_fields)

    item_fields = """    amount = Column(Float, nullable=True)
    amount_unit = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    is_optional = Column(Boolean, default=False)
    cart_quantity = Column(Integer, default=1)
    snapshot_price = Column(Float, nullable=True)"""
    if "snapshot_price = Column" not in text:
        text = insert_after(text, "    quantity = Column(Integer)", item_fields)

    models_path.write_text(text, encoding="utf-8")
    print("OK patched app/models.py")


def main() -> None:
    project_root = Path.cwd()
    patch_root = Path(__file__).resolve().parent
    if not (project_root / "app").exists() or not (project_root / "frontend").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto, poi esegui python install_profile_recipes_v7.py")
    copy_patch_files(project_root, patch_root)
    patch_models_py(project_root)
    patch_main_py(project_root)
    (project_root / "frontend" / "static" / "images" / "recipes").mkdir(parents=True, exist_ok=True)
    print("\nPatch Profilo + Ricette v7 installata.")
    print("Riavvia uvicorn e fai Ctrl+F5 nel browser.")
    print("Reimporta lo ZIP Lidl completo per salvare davvero flyer_valid_from/flyer_valid_to nei prodotti.")


if __name__ == "__main__":
    main()
