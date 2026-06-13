from __future__ import annotations

import shutil
from pathlib import Path

PATCH_FILES = [
    "app/routers/shopping_history.py",
    "frontend/js/products.js",
    "frontend/js/modal-function.js",
    "frontend/js/shopping.js",
    "frontend/history.html",
    "frontend/js/history.js",
    "frontend/js/history-all.js",
    "frontend/js/history-products.js",
    "frontend/css/history.css",
    "frontend/admin.html",
    "frontend/js/admin-role.js",
    "frontend/css/admin.css",
    "docs/HISTORY_PRODUCTS_POLISH_V19.md",
]


def copy_files(root: Path, patch_root: Path) -> None:
    for rel in PATCH_FILES:
        src = patch_root / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            backup = dst.with_suffix(dst.suffix + ".bak_history_products_polish_v19")
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

    backup = path.with_suffix(".py.bak_history_products_polish_v19")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")
    text = ensure_import(text, "from app.routers import shopping_history")

    if "app.include_router(shopping_history.router)" not in text:
        text = text.rstrip() + "\napp.include_router(shopping_history.router)\n"

    path.write_text(text, encoding="utf-8")
    print("OK patched app/main.py")


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "frontend").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto, dove esiste frontend/.")

    copy_files(root, patch_root)

    if (root / "app").exists():
        patch_main(root)

    print()
    print("Patch v19 installata.")
    print("Deploya il backend su Render e carica i file frontend aggiornati su SiteGround.")
    print("Controllo Swagger: GET /shopping-history/products")


if __name__ == "__main__":
    main()
