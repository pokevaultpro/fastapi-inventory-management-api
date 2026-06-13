from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PATCH_FILES = [
    "app/services/conad_flyer_cleanup.py",
    "app/routers/admin_cleanup.py",
    "frontend/js/conad-cleanup-admin-v26c.js",
    "frontend/css/conad-cleanup-admin-v26c.css",
    "docs/CLEANUP_CONAD_ONLINE_V26C.md",
]


def same_path(a: Path, b: Path) -> bool:
    try:
        return a.resolve().samefile(b.resolve())
    except FileNotFoundError:
        return False
    except OSError:
        return str(a.resolve()).lower() == str(b.resolve()).lower()


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

    backup = path.with_suffix(".py.bak_cleanup_online_v26c")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")
    text = ensure_import(text, "from app.routers import admin_cleanup")

    if "app.include_router(admin_cleanup.router)" not in text:
        text = text.rstrip() + "\napp.include_router(admin_cleanup.router)\n"

    path.write_text(text, encoding="utf-8")
    print("OK patched app/main.py")


def patch_admin_html(root: Path) -> None:
    path = root / "frontend" / "admin.html"
    if not path.exists():
        print("SKIP frontend/admin.html non trovato")
        return

    backup = path.with_suffix(".html.bak_cleanup_online_v26c")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")

    css_line = '<link rel="stylesheet" href="css/conad-cleanup-admin-v26c.css">'
    if css_line not in text:
        text = text.replace("</head>", f"  {css_line}\n</head>", 1)

    script_line = '<script type="module" src="js/conad-cleanup-admin-v26c.js"></script>'
    if script_line not in text:
        text = text.replace("</body>", f"{script_line}\n</body>", 1)

    path.write_text(text, encoding="utf-8")
    print("OK patched frontend/admin.html")


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
            backup = dst.with_suffix(dst.suffix + ".bak_cleanup_online_v26c")
            if not backup.exists():
                shutil.copy2(dst, backup)

        shutil.copy2(src, dst)
        print(f"OK copied {rel}")

    patch_main(root)
    patch_admin_html(root)

    for rel in [
        "app/services/conad_flyer_cleanup.py",
        "app/routers/admin_cleanup.py",
        "app/main.py",
    ]:
        py_compile.compile(str(root / rel), doraise=True)
        print(f"OK compile: {rel}")

    print()
    print("Patch v26c installata.")
    print("Fai commit/push/redeploy Render.")
    print("Carica su SiteGround:")
    print("- frontend/admin.html")
    print("- frontend/js/conad-cleanup-admin-v26c.js")
    print("- frontend/css/conad-cleanup-admin-v26c.css")


if __name__ == "__main__":
    main()
