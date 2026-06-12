from __future__ import annotations

import shutil
from pathlib import Path


PATCH_FILES = [
    "scripts/force_products_model_v17.py",
    "docs/FORCE_PRODUCTS_MODEL_V17.md",
]


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "app" / "models.py").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto, dove esiste app/models.py")

    for rel in PATCH_FILES:
        src = patch_root / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"OK copied {rel}")

    print()
    print("Ora esegui:")
    print("python scripts\\force_products_model_v17.py")
    print()
    print("Poi fai commit/push/deploy su Render.")
    print("Dopo deploy controlla: GET /admin/debug/products-model")


if __name__ == "__main__":
    main()
