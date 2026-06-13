from __future__ import annotations

import shutil
from pathlib import Path

PATCH_FILES = [
    "app/routers/admin.py",
    "app/routers/cart.py",
    "app/routers/shopping_history.py",
    "app/services/schema_compat.py",
    "frontend/admin.html",
    "frontend/css/admin.css",
    "frontend/css/products.css",
    "frontend/css/shopping.css",
    "frontend/css/history.css",
    "frontend/js/admin.js",
    "frontend/js/admin-role.js",
    "frontend/js/modal-function.js",
    "frontend/js/products.js",
    "frontend/js/shopping.js",
    "frontend/history.html",
    "frontend/js/history.js",
    "frontend/js/history-all.js",
    "frontend/js/history-products.js",
    "scripts/force_variable_pricing_model_v20.py",
    "scripts/migrate_variable_pricing_v20.py",
    "docs/VARIABLE_PRICING_V20.md",
]


def same_path(a: Path, b: Path) -> bool:
    try:
        return a.resolve().samefile(b.resolve())
    except FileNotFoundError:
        return False
    except OSError:
        return str(a.resolve()).lower() == str(b.resolve()).lower()


def copy_files(root: Path, patch_root: Path) -> None:
    for rel in PATCH_FILES:
        src = patch_root / rel
        dst = root / rel

        if not src.exists():
            print(f"SKIP source missing: {rel}")
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)

        if same_path(src, dst):
            print(f"OK already in place: {rel}")
            continue

        if dst.exists():
            backup = dst.with_suffix(dst.suffix + ".bak_variable_pricing_v20")
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


def patch_main(root: Path) -> None:
    path = root / "app" / "main.py"
    if not path.exists():
        print("SKIP app/main.py non trovato")
        return

    backup = path.with_suffix(".py.bak_variable_pricing_v20")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")
    text = ensure_import(text, "from app.routers import admin, cart, shopping_history")
    text = ensure_import(text, "from app.services.schema_compat import ensure_schema_compat")

    if "ensure_schema_compat(engine)" not in text and "Base.metadata.create_all(bind=engine)" in text:
        compat = (
            "\ntry:\n"
            "    ensure_schema_compat(engine)\n"
            "except Exception as exc:\n"
            "    print(f'Schema compatibility warning: {exc}')\n"
        )
        text = text.replace("Base.metadata.create_all(bind=engine)", "Base.metadata.create_all(bind=engine)" + compat, 1)

    for include in [
        "app.include_router(admin.router)",
        "app.include_router(cart.router)",
        "app.include_router(shopping_history.router)",
    ]:
        if include not in text:
            text = text.rstrip() + "\n" + include + "\n"

    path.write_text(text, encoding="utf-8")
    print("OK patched app/main.py")


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "app").exists() or not (root / "frontend").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto, dove esistono app/ e frontend/.")

    copy_files(root, patch_root)
    patch_main(root)

    print()
    print("Patch v20 installata.")
    print("Ora esegui:")
    print("python scripts\\force_variable_pricing_model_v20.py")
    print()
    print("Poi fai deploy backend su Render e carica i file frontend su SiteGround.")
    print("Su Render, se serve, puoi eseguire: python scripts/migrate_variable_pricing_v20.py")


if __name__ == "__main__":
    main()
