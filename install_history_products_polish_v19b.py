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

        # Important: if the zip was extracted directly into the project root,
        # src and dst are the same file. Copying a file onto itself can raise
        # WinError 32 on Windows, so we just skip it.
        if same_path(src, dst):
            print(f"OK already in place: {rel}")
            continue

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
        raise RuntimeError("Devi eseguire lo script dalla root del progetto, dove esiste frontend/.")

    copy_files(root, patch_root)

    if (root / "app").exists():
        patch_main(root)

    print()
    print("Patch v19b installata.")
    print("Se avevi estratto lo ZIP direttamente nella root, era normale vedere 'already in place'.")
    print("Ora deploya il backend su Render e carica i file frontend aggiornati su SiteGround.")
    print("Controllo Swagger: GET /shopping-history/products")


if __name__ == "__main__":
    main()
