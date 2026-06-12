from __future__ import annotations

import shutil
from pathlib import Path

PATCH_FILES = [
    "app/routers/admin.py",
    "app/services/schema_compat.py",
    "scripts/migrate_schema_compat_v16.py",
    "docs/ADMIN_PRODUCT_BACKEND_FIX_V16.md",
]


def copy_files(root: Path, patch_root: Path) -> None:
    for rel in PATCH_FILES:
        src = patch_root / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            backup = dst.with_suffix(dst.suffix + ".bak_admin_product_backend_fix_v16")
            if not backup.exists():
                shutil.copy2(dst, backup)
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


def replace_sqlalchemy_import(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("from sqlalchemy import "):
            items = [x.strip() for x in line.replace("from sqlalchemy import ", "").split(",")]
            if "Text" not in items:
                items.append("Text")
            new_line = "from sqlalchemy import " + ", ".join(dict.fromkeys(items))
            return text.replace(line, new_line, 1)
    return text


def insert_after(text: str, anchor: str, addition: str) -> str:
    marker = addition.strip().splitlines()[0].strip()
    if marker in text:
        return text
    if anchor not in text:
        return text
    return text.replace(anchor, anchor + "\n" + addition, 1)


def patch_models(root: Path) -> None:
    path = root / "app" / "models.py"
    if not path.exists():
        raise FileNotFoundError("Non trovo app/models.py")

    backup = path.with_suffix(".py.bak_admin_product_backend_fix_v16")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")
    text = replace_sqlalchemy_import(text)

    product_fields = (
        "    brand = Column(String, nullable=True)\n"
        "    flyer_page = Column(Integer, nullable=True)\n"
        "    flyer_valid_from = Column(String, nullable=True)\n"
        "    flyer_valid_to = Column(String, nullable=True)\n"
        "    flyer_source = Column(String, nullable=True)\n"
        "    flyer_source_url = Column(Text, nullable=True)\n"
        "    is_lidl_plus = Column(Boolean, default=False)\n"
        "    flyer_imported_at = Column(String, nullable=True)\n"
        "    offer_note = Column(Text, nullable=True)\n"
        "    discount_percent = Column(Float, nullable=True)"
    )

    if "brand = Column" not in text or "flyer_valid_from = Column" not in text:
        if "    location = Column(String, nullable=True)" in text:
            text = insert_after(text, "    location = Column(String, nullable=True)", product_fields)
        elif "    supermarket = relationship" in text:
            text = text.replace("    supermarket = relationship", product_fields + "\n\n    supermarket = relationship", 1)

    recipe_fields = (
        "    description = Column(Text, nullable=True)\n"
        "    servings = Column(Integer, default=1)\n"
        "    prep_time_minutes = Column(Integer, nullable=True)\n"
        "    instructions = Column(Text, nullable=True)\n"
        "    source_type = Column(String, default=\"personal\")\n"
        "    source_url = Column(Text, nullable=True)\n"
        "    estimated_total = Column(Float, nullable=True)\n"
        "    created_at = Column(String, nullable=True)"
    )

    if "prep_time_minutes = Column" not in text and "class Recipes" in text:
        if "    image = Column(String, nullable=True)" in text:
            text = insert_after(text, "    image = Column(String, nullable=True)", recipe_fields)

    item_fields = (
        "    amount = Column(Float, nullable=True)\n"
        "    amount_unit = Column(String, nullable=True)\n"
        "    note = Column(Text, nullable=True)\n"
        "    is_optional = Column(Boolean, default=False)\n"
        "    cart_quantity = Column(Integer, default=1)\n"
        "    snapshot_price = Column(Float, nullable=True)"
    )

    if "snapshot_price = Column" not in text and "class RecipeItems" in text:
        if "    quantity = Column(Integer)" in text:
            text = insert_after(text, "    quantity = Column(Integer)", item_fields)

    path.write_text(text, encoding="utf-8")
    print("OK patched app/models.py")


def patch_main(root: Path) -> None:
    path = root / "app" / "main.py"
    if not path.exists():
        raise FileNotFoundError("Non trovo app/main.py")

    backup = path.with_suffix(".py.bak_admin_product_backend_fix_v16")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")
    text = ensure_import(text, "from app.routers import admin")
    text = ensure_import(text, "from app.services.schema_compat import ensure_schema_compat")

    compat = (
        "\ntry:\n"
        "    ensure_schema_compat(engine)\n"
        "except Exception as exc:\n"
        "    print(f'Schema compatibility warning: {exc}')\n"
    )
    if "ensure_schema_compat(engine)" not in text:
        if "Base.metadata.create_all(bind=engine)" in text:
            text = text.replace("Base.metadata.create_all(bind=engine)", "Base.metadata.create_all(bind=engine)" + compat, 1)
        else:
            text += "\nBase.metadata.create_all(bind=engine)" + compat + "\n"

    if "app.include_router(admin.router)" not in text:
        text = text.rstrip() + "\napp.include_router(admin.router)\n"

    path.write_text(text, encoding="utf-8")
    print("OK patched app/main.py")


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "app").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto backend, dove esiste la cartella app/.")

    copy_files(root, patch_root)
    patch_models(root)
    patch_main(root)

    print()
    print("Patch v16 installata.")
    print("Ora fai deploy su Render e riavvia il backend.")
    print("Controllo utile in Swagger: GET /admin/debug/products-model deve dare has_brand=true.")


if __name__ == "__main__":
    main()
