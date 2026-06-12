from __future__ import annotations

import shutil
from pathlib import Path

PATCH_FILES = [
    "frontend/admin.html",
    "frontend/js/admin.js",
    "frontend/css/admin.css",
    "docs/ADMIN_PRODUCT_FIELDS_V15.md",
]


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "frontend").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto, dove esiste la cartella frontend/.")

    for rel in PATCH_FILES:
        src = patch_root / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            backup = dst.with_suffix(dst.suffix + ".bak_admin_product_fields_v15")
            if not backup.exists():
                shutil.copy2(dst, backup)
        shutil.copy2(src, dst)
        print(f"OK copied {rel}")

    print()
    print("Patch v15 installata.")
    print("Riavvia/deploya e fai Ctrl+F5 su admin.html.")
    print("Ora il form prodotto mostra l'errore preciso se manca qualcosa o il backend rifiuta il salvataggio.")


if __name__ == "__main__":
    main()
