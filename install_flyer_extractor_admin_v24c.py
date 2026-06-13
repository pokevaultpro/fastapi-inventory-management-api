from __future__ import annotations

import shutil
from pathlib import Path

PATCH_FILES = [
    "frontend/js/flyer-extractor-admin-v24c.js",
    "frontend/css/flyer-extractor-admin-v24c.css",
    "docs/FLYER_EXTRACTOR_ADMIN_V24C.md",
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
            backup = dst.with_suffix(dst.suffix + ".bak_flyer_admin_v24c")
            if not backup.exists():
                shutil.copy2(dst, backup)

        shutil.copy2(src, dst)
        print(f"OK copied {rel}")


def remove_line_containing(text: str, needle: str) -> str:
    return "\n".join(line for line in text.splitlines() if needle not in line) + "\n"


def patch_admin_html(root: Path) -> None:
    path = root / "frontend" / "admin.html"
    if not path.exists():
        raise RuntimeError("Non trovo frontend/admin.html")

    backup = path.with_suffix(".html.bak_flyer_admin_v24c")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")

    # Remove old experimental flyer scripts/standalone link to avoid duplicates.
    for needle in [
        "flyer-extractor-admin.js",
        "flyer-extractor-admin-link.js",
        "flyer-extractor-page.js",
        "flyer-extractor-admin.css",
        "flyer-extractor-page.css",
    ]:
        text = remove_line_containing(text, needle)

    css_line = '<link rel="stylesheet" href="css/flyer-extractor-admin-v24c.css">'
    if css_line not in text:
        if "</head>" in text:
            text = text.replace("</head>", f"  {css_line}\n</head>", 1)
        else:
            text = css_line + "\n" + text

    script_line = '<script type="module" src="js/flyer-extractor-admin-v24c.js"></script>'
    if script_line not in text:
        if "</body>" in text:
            text = text.replace("</body>", f"{script_line}\n</body>", 1)
        else:
            text = text.rstrip() + "\n" + script_line + "\n"

    path.write_text(text, encoding="utf-8")
    print("OK patched frontend/admin.html con tab Volantini integrata")


def cleanup_standalone_files(root: Path) -> None:
    # Local cleanup of the previous standalone page. If it was uploaded to SiteGround,
    # delete those files manually there too.
    to_remove = [
        "frontend/flyer-extractor.html",
        "frontend/js/flyer-extractor-page.js",
        "frontend/js/flyer-extractor-admin-link.js",
        "frontend/css/flyer-extractor-page.css",
    ]
    for rel in to_remove:
        path = root / rel
        if path.exists():
            try:
                path.unlink()
                print(f"OK removed old standalone file: {rel}")
            except Exception as exc:
                print(f"SKIP remove {rel}: {exc}")


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (root / "frontend").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto, dove esiste frontend/.")

    copy_files(root, patch_root)
    patch_admin_html(root)
    cleanup_standalone_files(root)

    print()
    print("Patch v24c installata.")
    print("Questa versione NON usa flyer-extractor.html.")
    print("Carica su SiteGround:")
    print("- frontend/admin.html")
    print("- frontend/js/flyer-extractor-admin-v24c.js")
    print("- frontend/css/flyer-extractor-admin-v24c.css")
    print()
    print("Poi apri admin.html e fai Ctrl+F5. Vedrai la tab/bottone Volantini dentro Admin.")


if __name__ == "__main__":
    main()
