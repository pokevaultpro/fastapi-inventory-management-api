from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PATCH_FILES = [
    "app/routers/flyer_offer_image_zip_repair.py",
    "frontend/js/flyer-offer-images-zip-repair-v26j.js",
    "frontend/css/flyer-offer-images-zip-repair-v26j.css",
    "docs/REPAIR_PRODUCT_IMAGES_FROM_ZIP_V26J.md",
]


def same_file(a: Path, b: Path) -> bool:
    try:
        return a.resolve().samefile(b.resolve())
    except FileNotFoundError:
        return False
    except OSError:
        return str(a.resolve()).lower() == str(b.resolve()).lower()


def copy_if_needed(src: Path, dst: Path, rel: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if same_file(src, dst):
        print(f"OK already in place: {rel}")
        return

    if dst.exists():
        backup = dst.with_suffix(dst.suffix + ".bak_zip_image_repair_v26j")
        if not backup.exists():
            shutil.copy2(dst, backup)

    shutil.copy2(src, dst)
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
        raise RuntimeError("Non trovo app/main.py")

    backup = path.with_suffix(".py.bak_zip_image_repair_v26j")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")
    text = ensure_import(text, "from app.routers import flyer_offer_image_zip_repair")

    if "app.include_router(flyer_offer_image_zip_repair.router)" not in text:
        text = text.rstrip() + "\napp.include_router(flyer_offer_image_zip_repair.router)\n"

    path.write_text(text, encoding="utf-8")
    print("OK patched app/main.py")


def patch_flyer_page(root: Path) -> None:
    path = root / "frontend" / "flyer_offers.html"
    if not path.exists():
        print("SKIP frontend/flyer_offers.html non trovato")
        return

    backup = path.with_suffix(".html.bak_zip_image_repair_v26j")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")
    css = '<link rel="stylesheet" href="css/flyer-offer-images-zip-repair-v26j.css" />'
    script = '<script type="module" src="js/flyer-offer-images-zip-repair-v26j.js"></script>'

    if css not in text:
        text = text.replace("</head>", f"  {css}\n</head>", 1)

    if script not in text:
        text = text.replace("</body>", f"  {script}\n</body>", 1)

    path.write_text(text, encoding="utf-8")
    print("OK patched frontend/flyer_offers.html")


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "app").exists() or not (root / "frontend").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto, dove esistono app/ e frontend/.")

    for rel in PATCH_FILES:
        copy_if_needed(patch_root / rel, root / rel, rel)

    patch_main(root)
    patch_flyer_page(root)

    for rel in ["app/routers/flyer_offer_image_zip_repair.py", "app/main.py"]:
        py_compile.compile(str(root / rel), doraise=True)
        print(f"OK compile: {rel}")

    print()
    print("Patch v26j installata.")
    print("Fai commit/push/redeploy Render.")
    print("Carica su SiteGround:")
    print("- frontend/flyer_offers.html")
    print("- frontend/js/flyer-offer-images-zip-repair-v26j.js")
    print("- frontend/css/flyer-offer-images-zip-repair-v26j.css")


if __name__ == "__main__":
    main()
