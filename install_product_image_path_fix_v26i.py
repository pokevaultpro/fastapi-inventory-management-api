from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PATCH_FILES = [
    "app/routers/flyer_offer_page_admin.py",
    "frontend/js/flyer-offers-page-v26h.js",
    "frontend/css/flyer-offers-page-v26h.css",
    "docs/PRODUCT_IMAGE_PATH_FIX_V26I.md",
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
        backup = dst.with_suffix(dst.suffix + ".bak_product_image_path_v26i")
        if not backup.exists():
            shutil.copy2(dst, backup)

    shutil.copy2(src, dst)
    print(f"OK copied: {rel}")


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "app").exists() or not (root / "frontend").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto, dove esistono app/ e frontend/.")

    for rel in PATCH_FILES:
        copy_if_needed(patch_root / rel, root / rel, rel)

    py_compile.compile(str(root / "app/routers/flyer_offer_page_admin.py"), doraise=True)
    print("OK compile: app/routers/flyer_offer_page_admin.py")

    print()
    print("Patch v26i installata.")
    print("Fai commit/push/redeploy Render.")
    print("Carica su SiteGround:")
    print("- frontend/js/flyer-offers-page-v26h.js")
    print("- frontend/css/flyer-offers-page-v26h.css")


if __name__ == "__main__":
    main()
