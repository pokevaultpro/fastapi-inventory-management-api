from __future__ import annotations

from pathlib import Path
import shutil
import re

PATCH_FILES = [
    "app/routers/recipe_smart.py",
    "app/routers/weekly_menus.py",
    "app/services/schema_compat.py",
    "frontend/recipes.html",
    "frontend/js/recipes.js",
    "frontend/css/recipes.css",
    "frontend/weekly-menu.html",
    "frontend/js/weekly-menu.js",
    "frontend/css/weekly-menu.css",
    "scripts/migrate_nutrition_v28.py",
    "docs/NUTRITION_V28.md",
]


def same_path(a: Path, b: Path) -> bool:
    try:
        return a.resolve().samefile(b.resolve())
    except FileNotFoundError:
        return False
    except OSError:
        try:
            return str(a.resolve()).lower() == str(b.resolve()).lower()
        except OSError:
            return False


def copy_file(src: Path, dst: Path, rel: str) -> None:
    if not src.exists():
        print(f"SKIP missing: {rel}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and same_path(src, dst):
        print(f"OK already in place: {rel}")
        return
    if dst.exists():
        backup = dst.with_suffix(dst.suffix + ".bak_nutrition_v28")
        if not backup.exists() and not same_path(dst, backup):
            try:
                shutil.copyfile(dst, backup)
            except Exception:
                backup.write_bytes(dst.read_bytes())
    try:
        shutil.copyfile(src, dst)
    except Exception:
        dst.write_bytes(src.read_bytes())
    print(f"OK copied: {rel}")


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
    text = path.read_text(encoding="utf-8")
    text = ensure_import(text, "from app.routers import recipe_smart")
    text = ensure_import(text, "from app.routers import weekly_menus as smartgrocery_weekly_menus")
    if "app.include_router(recipe_smart.router)" not in text:
        text = text.rstrip() + "\napp.include_router(recipe_smart.router)\n"
    if "app.include_router(smartgrocery_weekly_menus.router)" not in text:
        text = text.rstrip() + "\napp.include_router(smartgrocery_weekly_menus.router)\n"
    path.write_text(text, encoding="utf-8")
    print("OK patched: app/main.py")


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent
    if not (root / "app").exists() or not (root / "frontend").exists():
        raise RuntimeError("Estrai lo ZIP nella root progetto, dove esistono app/ e frontend/.")
    for rel in PATCH_FILES:
        copy_file(patch_root / rel, root / rel, rel)
    patch_main(root)
    print()
    print("Patch v28 nutrizione installata.")
    print("Ora esegui opzionale:")
    print("python scripts/migrate_nutrition_v28.py")
    print("Poi git add . && git commit -m \"Add recipe nutrition and weekly macro summary\" && git push")
    print("Su SiteGround carica: recipes.html, weekly-menu.html, js/recipes.js, js/weekly-menu.js, css/recipes.css, css/weekly-menu.css")


if __name__ == "__main__":
    main()
