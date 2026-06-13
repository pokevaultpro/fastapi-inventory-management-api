from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PATCH_FILES = [
    "scripts/cleanup_conad_flyer_products_v26b.py",
    "docs/CLEANUP_CONAD_FLYER_PRODUCTS_V26B.md",
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

    if not (root / "app").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto, dove esiste app/.")

    for rel in PATCH_FILES:
        src = patch_root / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)

        if same_path(src, dst):
            print(f"OK already in place: {rel}")
            continue

        if dst.exists():
            backup = dst.with_suffix(dst.suffix + ".bak_cleanup_conad_v26b")
            if not backup.exists():
                shutil.copy2(dst, backup)

        shutil.copy2(src, dst)
        print(f"OK copied {rel}")

    py_compile.compile(str(root / "scripts/cleanup_conad_flyer_products_v26b.py"), doraise=True)
    print()
    print("Cleanup script installato.")
    print("Prima fai dry-run:")
    print("python scripts\\cleanup_conad_flyer_products_v26b.py")
    print()
    print("Poi, se il conteggio è giusto:")
    print("python scripts\\cleanup_conad_flyer_products_v26b.py --execute")


if __name__ == "__main__":
    main()
