from __future__ import annotations

import shutil
from pathlib import Path

PATCH_FILES = [
    "app/routers/shopping_history.py",
    "frontend/history.html",
    "frontend/js/history.js",
    "frontend/css/history.css",
    "frontend/js/navbar.js",
    "frontend/js/quick-actions.js",
    "frontend/css/bottom-bar.css",
    "docs/SHOPPING_HISTORY_ANALYTICS.md",
]


def backup_file(path: Path) -> None:
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak_history_patch")
        if not backup.exists():
            shutil.copy2(path, backup)
            print(f"Backup: {backup}")


def copy_files(project_root: Path, patch_root: Path) -> None:
    for rel in PATCH_FILES:
        src = patch_root / rel
        dst = project_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        backup_file(dst)
        shutil.copy2(src, dst)
        print(f"OK copied {rel}")


def main() -> None:
    project_root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (project_root / "app").exists() or not (project_root / "frontend").exists():
        raise RuntimeError("Esegui questo installer dalla root del progetto, dove ci sono app/ e frontend/.")

    copy_files(project_root, patch_root)

    print()
    print("Patch cronologia installata.")
    print("Riavvia FastAPI e apri frontend/history.html")
    print("Endpoint da verificare in /docs: GET /shopping-history/stats")


if __name__ == "__main__":
    main()
