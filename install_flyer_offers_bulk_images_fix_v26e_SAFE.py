from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PATCH_FILES = [
    "app/services/flyer_offer_importer.py",
    "app/routers/flyer_offer_admin.py",
    "frontend/js/flyer-offers-admin-v26.js",
    "frontend/css/flyer-offers-admin-v26.css",
    "docs/FLYER_OFFERS_BULK_IMAGES_FIX_V26E.md",
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

    # Importantissimo su Windows:
    # se hai estratto lo ZIP direttamente nella root del progetto,
    # src e dst sono lo stesso file. In quel caso NON bisogna fare copy2.
    if same_file(src, dst):
        print(f"OK already in place: {rel}")
        return

    if not src.exists():
        print(f"SKIP source missing: {rel}")
        return

    if dst.exists():
        backup = dst.with_suffix(dst.suffix + ".bak_bulk_images_v26e")
        if not backup.exists() and not same_file(dst, backup):
            shutil.copy2(dst, backup)

    shutil.copy2(src, dst)
    print(f"OK copied: {rel}")


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "app").exists() or not (root / "frontend").exists():
        raise RuntimeError("Esegui questo file dalla root del progetto, dove esistono app/ e frontend/.")

    for rel in PATCH_FILES:
        copy_if_needed(patch_root / rel, root / rel, rel)

    for rel in ["app/services/flyer_offer_importer.py", "app/routers/flyer_offer_admin.py"]:
        path = root / rel
        if path.exists():
            py_compile.compile(str(path), doraise=True)
            print(f"OK compile: {rel}")
        else:
            print(f"ATTENZIONE: non trovo {rel}")

    print()
    print("Safe installer completato.")
    print("Ora carica su SiteGround:")
    print("- frontend/js/flyer-offers-admin-v26.js")
    print("- frontend/css/flyer-offers-admin-v26.css")
    print()
    print("Poi commit/push/redeploy Render.")


if __name__ == "__main__":
    main()
