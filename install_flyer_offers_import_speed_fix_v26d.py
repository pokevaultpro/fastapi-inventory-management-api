from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PATCH_FILES = [
    "app/services/flyer_offer_importer.py",
    "frontend/js/flyer-offers-admin-v26.js",
    "frontend/css/flyer-offers-admin-v26.css",
    "docs/FLYER_OFFERS_IMPORT_SPEED_FIX_V26D.md",
]


def same_path(a: Path, b: Path) -> bool:
    try:
        return a.resolve().samefile(b.resolve())
    except FileNotFoundError:
        return False
    except OSError:
        return str(a.resolve()).lower() == str(b.resolve()).lower()


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "app").exists() or not (root / "frontend").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto, dove esistono app/ e frontend/.")

    for rel in PATCH_FILES:
        src = patch_root / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)

        if same_path(src, dst):
            print(f"OK already in place: {rel}")
            continue

        if dst.exists():
            backup = dst.with_suffix(dst.suffix + ".bak_import_speed_v26d")
            if not backup.exists():
                shutil.copy2(dst, backup)

        shutil.copy2(src, dst)
        print(f"OK copied {rel}")

    py_compile.compile(str(root / "app/services/flyer_offer_importer.py"), doraise=True)
    print()
    print("Patch v26d installata.")
    print("Fai commit/push/redeploy Render.")
    print("Carica su SiteGround:")
    print("- frontend/js/flyer-offers-admin-v26.js")
    print("- frontend/css/flyer-offers-admin-v26.css")


if __name__ == "__main__":
    main()
