from __future__ import annotations

import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

PATCH_FILES = [
    "app/services/flyer_offer_schema.py",
    "app/services/flyer_offer_importer.py",
    "app/routers/flyer_offer_admin.py",
    "app/routers/flyer_offer_public.py",
    "frontend/js/flyer-offers-admin-v26.js",
    "frontend/css/flyer-offers-admin-v26.css",
    "scripts/migrate_flyer_offers_v26.py",
    "scripts/force_product_flyer_fields_v26.py",
    "docs/FLYER_OFFERS_WORKFLOW_V26.md",
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
        dst.parent.mkdir(parents=True, exist_ok=True)

        if same_path(src, dst):
            print(f"OK already in place: {rel}")
            continue

        if dst.exists():
            backup = dst.with_suffix(dst.suffix + ".bak_flyer_offers_v26")
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

    backup = path.with_suffix(".py.bak_flyer_offers_v26")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")
    text = ensure_import(text, "from app.routers import flyer_offer_admin, flyer_offer_public")

    if "app.include_router(flyer_offer_admin.router)" not in text:
        text = text.rstrip() + "\napp.include_router(flyer_offer_admin.router)\n"
    if "app.include_router(flyer_offer_public.router)" not in text:
        text = text.rstrip() + "\napp.include_router(flyer_offer_public.router)\n"

    path.write_text(text, encoding="utf-8")
    print("OK patched app/main.py")


def patch_admin_html(root: Path) -> None:
    path = root / "frontend" / "admin.html"
    if not path.exists():
        print("SKIP frontend/admin.html non trovato")
        return

    backup = path.with_suffix(".html.bak_flyer_offers_v26")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")

    css_line = '<link rel="stylesheet" href="css/flyer-offers-admin-v26.css">'
    if css_line not in text:
        if "</head>" in text:
            text = text.replace("</head>", f"  {css_line}\n</head>", 1)
        else:
            text = css_line + "\n" + text

    script_line = '<script type="module" src="js/flyer-offers-admin-v26.js"></script>'
    if script_line not in text:
        if "</body>" in text:
            text = text.replace("</body>", f"{script_line}\n</body>", 1)
        else:
            text = text.rstrip() + "\n" + script_line + "\n"

    path.write_text(text, encoding="utf-8")
    print("OK patched frontend/admin.html")


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "app").exists() or not (root / "frontend").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto, dove esistono app/ e frontend/.")

    copy_files(root, patch_root)
    patch_main(root)
    patch_admin_html(root)

    subprocess.run([sys.executable, "scripts/force_product_flyer_fields_v26.py"], check=True)
    subprocess.run([sys.executable, "scripts/migrate_flyer_offers_v26.py"], check=True)

    for rel in [
        "app/services/flyer_offer_schema.py",
        "app/services/flyer_offer_importer.py",
        "app/routers/flyer_offer_admin.py",
        "app/routers/flyer_offer_public.py",
        "scripts/migrate_flyer_offers_v26.py",
        "scripts/force_product_flyer_fields_v26.py",
    ]:
        py_compile.compile(str(root / rel), doraise=True)
        print(f"OK compile: {rel}")

    print()
    print("Patch v26 installata.")
    print("Fai commit/push/redeploy Render.")
    print("Carica su SiteGround:")
    print("- frontend/admin.html")
    print("- frontend/js/flyer-offers-admin-v26.js")
    print("- frontend/css/flyer-offers-admin-v26.css")
    print()
    print("Su Render Shell puoi rilanciare:")
    print("python scripts/migrate_flyer_offers_v26.py")


if __name__ == "__main__":
    main()
