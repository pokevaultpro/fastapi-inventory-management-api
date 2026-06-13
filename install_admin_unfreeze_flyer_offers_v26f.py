from __future__ import annotations

import shutil
from pathlib import Path

PATCH_FILES = [
    "frontend/js/flyer-offers-admin-v26.js",
    "frontend/css/flyer-offers-admin-v26.css",
    "docs/ADMIN_UNFREEZE_FLYER_OFFERS_V26F.md",
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
        backup = dst.with_suffix(dst.suffix + ".bak_admin_unfreeze_v26f")
        if not backup.exists():
            shutil.copy2(dst, backup)

    shutil.copy2(src, dst)
    print(f"OK copied: {rel}")


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "frontend").exists():
        raise RuntimeError("Esegui dalla root del progetto, dove esiste frontend/.")

    for rel in PATCH_FILES:
        copy_if_needed(patch_root / rel, root / rel, rel)

    print()
    print("Hotfix v26f installato.")
    print("Carica su SiteGround:")
    print("- frontend/js/flyer-offers-admin-v26.js")
    print("- frontend/css/flyer-offers-admin-v26.css")
    print()
    print("Poi apri admin in finestra anonima o fai Ctrl+F5.")


if __name__ == "__main__":
    main()
