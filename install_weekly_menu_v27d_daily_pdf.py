from __future__ import annotations

from pathlib import Path
import shutil

PATCH_FILES = [
    "app/routers/weekly_menus.py",
    "frontend/weekly-menu.html",
    "frontend/js/weekly-menu.js",
    "frontend/css/weekly-menu.css",
    "scripts/migrate_weekly_menu_v27.py",
    "docs/WEEKLY_MENU_V27.md",
]


def is_same_path(src: Path, dst: Path) -> bool:
    try:
        return src.resolve().samefile(dst.resolve())
    except FileNotFoundError:
        return False
    except OSError:
        try:
            return str(src.resolve()).lower() == str(dst.resolve()).lower()
        except OSError:
            return False


def safe_copy(src: Path, dst: Path, rel: str) -> None:
    if not src.exists():
        print(f"SKIP missing in patch: {rel}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists() and is_same_path(src, dst):
        print(f"OK already in place: {rel}")
        return

    if dst.exists():
        backup = dst.with_suffix(dst.suffix + ".bak_weekly_menu_v27")
        if not backup.exists() and not is_same_path(dst, backup):
            try:
                shutil.copyfile(dst, backup)
            except Exception:
                try:
                    backup.write_bytes(dst.read_bytes())
                except Exception:
                    print(f"WARN backup skipped: {rel}")

    try:
        shutil.copyfile(src, dst)
    except Exception:
        dst.write_bytes(src.read_bytes())
    print(f"OK copied: {rel}")


def patch_main(root: Path) -> None:
    main_path = root / "app" / "main.py"
    if not main_path.exists():
        raise RuntimeError("Non trovo app/main.py. Lancia l'installer dalla root del progetto.")

    text = main_path.read_text(encoding="utf-8")
    marker = "# SmartGrocery weekly menu v27"
    if marker in text:
        print("OK app/main.py già patchato")
        return

    block = """

# SmartGrocery weekly menu v27
from app.routers import weekly_menus as smartgrocery_weekly_menus
app.include_router(smartgrocery_weekly_menus.router)
"""
    main_path.write_text(text.rstrip() + block + "\n", encoding="utf-8")
    print("OK patched: app/main.py include weekly_menus router")


def patch_navbar(root: Path) -> None:
    nav_path = root / "frontend" / "js" / "navbar.js"
    if not nav_path.exists():
        print("SKIP navbar.js non trovato")
        return

    text = nav_path.read_text(encoding="utf-8")
    if "weekly-menu.html" in text:
        print("OK navbar.js già contiene weekly-menu")
        return

    needle = 'if (tab === "recipes") window.location.href = "recipes.html";'
    if needle in text:
        text = text.replace(
            needle,
            needle + '\n  if (tab === "weekly-menu" || tab === "menu") window.location.href = "weekly-menu.html";'
        )
        nav_path.write_text(text, encoding="utf-8")
        print("OK patched: frontend/js/navbar.js route weekly-menu")
    else:
        print("SKIP navbar.js: struttura non riconosciuta, weekly-menu resta accessibile da URL diretto")


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "app").exists() or not (root / "frontend").exists():
        raise RuntimeError("Lancia l'installer dalla root progetto, dove esistono app/ e frontend/.")

    for rel in PATCH_FILES:
        safe_copy(patch_root / rel, root / rel, rel)

    patch_main(root)
    patch_navbar(root)

    print()
    print("Patch v27h installata.")
    print("Note menu-specifiche nel PDF.")
    print("Poi fai commit/push/redeploy Render.")
    print("Su SiteGround carica:")
    print("- frontend/weekly-menu.html")
    print("- frontend/js/weekly-menu.js")
    print("- frontend/css/weekly-menu.css")


if __name__ == "__main__":
    main()
