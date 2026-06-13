from __future__ import annotations

import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

PATCH_FILES = [
    "frontend/admin.html",
    "scripts/patch_static_mount_v24e.py",
    "docs/FLYER_EXTRACTOR_STATIC_AUTH_FIX_V24E.md",
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
            backup = dst.with_suffix(dst.suffix + ".bak_flyer_static_auth_v24e")
            if not backup.exists():
                shutil.copy2(dst, backup)

        shutil.copy2(src, dst)
        print(f"OK copied {rel}")

    subprocess.run([sys.executable, "scripts/patch_static_mount_v24e.py"], check=True)

    for rel in ["app/main.py", "scripts/patch_static_mount_v24e.py"]:
        py_compile.compile(str(root / rel), doraise=True)
        print(f"OK compile: {rel}")

    print()
    print("Patch v24e installata.")
    print("Fai commit/push/redeploy Render per montare /static.")
    print("Carica frontend/admin.html su SiteGround e fai Ctrl+F5.")


if __name__ == "__main__":
    main()
