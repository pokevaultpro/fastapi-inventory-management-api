from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PATCH_FILES = [
    "app/routers/flyer_extractor.py",
    "frontend/js/flyer-extractor-admin.js",
    "frontend/css/flyer-extractor-admin.css",
    "scripts/flyer_image_extractor_local_v24.py",
    "docs/FLYER_IMAGE_EXTRACTOR_V24.md",
]


def same_path(a: Path, b: Path) -> bool:
    try:
        return a.resolve().samefile(b.resolve())
    except FileNotFoundError:
        return False
    except OSError:
        return str(a.resolve()).lower() == str(b.resolve()).lower()


def copy_files(root: Path, patch_root: Path) -> None:
    for rel in PATCH_FILES:
        src = patch_root / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)

        if same_path(src, dst):
            print(f"OK already in place: {rel}")
            continue

        if dst.exists():
            backup = dst.with_suffix(dst.suffix + ".bak_flyer_extractor_v24")
            if not backup.exists():
                shutil.copy2(dst, backup)

        shutil.copy2(src, dst)
        print(f"OK copied {rel}")


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
        print("SKIP app/main.py non trovato")
        return

    backup = path.with_suffix(".py.bak_flyer_extractor_v24")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")
    text = ensure_import(text, "from app.routers import flyer_extractor")

    if "app.include_router(flyer_extractor.router)" not in text:
        text = text.rstrip() + "\napp.include_router(flyer_extractor.router)\n"

    path.write_text(text, encoding="utf-8")
    print("OK patched app/main.py")


def patch_admin_html(root: Path) -> None:
    path = root / "frontend" / "admin.html"
    if not path.exists():
        print("SKIP frontend/admin.html non trovato")
        return

    backup = path.with_suffix(".html.bak_flyer_extractor_v24")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")

    css_line = '<link rel="stylesheet" href="css/flyer-extractor-admin.css">'
    if css_line not in text:
        if "</head>" in text:
            text = text.replace("</head>", f"  {css_line}\n</head>", 1)
        else:
            text = css_line + "\n" + text

    script_line = '<script type="module" src="js/flyer-extractor-admin.js"></script>'
    if script_line not in text:
        if "</body>" in text:
            text = text.replace("</body>", f"{script_line}\n</body>", 1)
        else:
            text = text.rstrip() + "\n" + script_line + "\n"

    path.write_text(text, encoding="utf-8")
    print("OK patched frontend/admin.html")


def patch_requirements(root: Path) -> None:
    path = root / "requirements.txt"
    if not path.exists():
        path.write_text("PyMuPDF>=1.24.0\nPillow>=10.0.0\n", encoding="utf-8")
        print("OK created requirements.txt")
        return

    backup = path.with_suffix(".txt.bak_flyer_extractor_v24")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")
    additions = []
    lower = text.lower()
    if "pymupdf" not in lower and "fitz" not in lower:
        additions.append("PyMuPDF>=1.24.0")
    if "pillow" not in lower and "\npil" not in lower:
        additions.append("Pillow>=10.0.0")

    if additions:
        text = text.rstrip() + "\n" + "\n".join(additions) + "\n"
        path.write_text(text, encoding="utf-8")
        print("OK patched requirements.txt")
    else:
        print("requirements.txt già contiene PyMuPDF/Pillow")


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "app").exists() or not (root / "frontend").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto, dove esistono app/ e frontend/.")

    copy_files(root, patch_root)
    patch_main(root)
    patch_admin_html(root)
    patch_requirements(root)

    for rel in [
        "app/routers/flyer_extractor.py",
        "scripts/flyer_image_extractor_local_v24.py",
    ]:
        py_compile.compile(str(root / rel), doraise=True)
        print(f"OK compile: {rel}")

    print()
    print("Patch v24 installata.")
    print("Ora fai commit/push/redeploy su Render.")
    print("Poi in admin.html apri la tab Volantini.")
    print("Controllo Swagger: GET /admin/flyer-extractor/health")


if __name__ == "__main__":
    main()
