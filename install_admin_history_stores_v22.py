from __future__ import annotations

import shutil
from pathlib import Path

PATCH_FILES = [
    "app/routers/admin_history.py",
    "frontend/admin.html",
    "frontend/css/admin.css",
    "frontend/js/admin-history.js",
    "frontend/supermarkets.html",
    "frontend/css/supermarkets.css",
    "frontend/js/supermarkets.js",
    "docs/ADMIN_HISTORY_STORES_REDESIGN_V22.md",
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
            backup = dst.with_suffix(dst.suffix + ".bak_admin_history_stores_v22")
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

    backup = path.with_suffix(".py.bak_admin_history_stores_v22")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")
    text = ensure_import(text, "from app.routers import admin_history")

    if "app.include_router(admin_history.router)" not in text:
        text = text.rstrip() + "\napp.include_router(admin_history.router)\n"

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
    print("Patch v22 installata.")
    print("Deploya backend su Render e carica frontend aggiornato su SiteGround.")
    print("Controlli Swagger: GET /admin/history/debug e GET /admin/history/users")


if __name__ == "__main__":
    main()
