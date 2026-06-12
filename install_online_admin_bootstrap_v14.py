from __future__ import annotations

import shutil
from pathlib import Path

PATCH_FILES = [
    "app/routers/admin_bootstrap.py",
    "app/routers/profile_role.py",
    "frontend/js/profile-role-v14.js",
    "docs/ONLINE_ADMIN_BOOTSTRAP_V14.md",
]


def copy_files(root: Path, patch_root: Path) -> None:
    for rel in PATCH_FILES:
        src = patch_root / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
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
    p = root / "app" / "main.py"
    if not p.exists():
        raise FileNotFoundError("Non trovo app/main.py")
    backup = p.with_suffix(".py.bak_online_admin_bootstrap_v14")
    if not backup.exists():
        shutil.copy2(p, backup)

    text = p.read_text(encoding="utf-8")
    text = ensure_import(text, "from app.routers import admin_bootstrap, profile_role")

    for include in [
        "app.include_router(profile_role.router)",
        "app.include_router(admin_bootstrap.router)",
    ]:
        if include not in text:
            text = text.rstrip() + "\n" + include + "\n"

    p.write_text(text, encoding="utf-8")
    print("OK patched app/main.py")


def patch_profile_html(root: Path) -> None:
    p = root / "frontend" / "profile.html"
    if not p.exists():
        print("SKIP frontend/profile.html non trovato")
        return

    backup = p.with_suffix(".html.bak_online_admin_bootstrap_v14")
    if not backup.exists():
        shutil.copy2(p, backup)

    text = p.read_text(encoding="utf-8")
    for old in [
        '<script type="module" src="js/profile-role-badge.js"></script>',
        '<script type="module" src="js/profile-role-v13.js"></script>',
        '<script type="module" src="js/profile-role-v14.js"></script>',
    ]:
        text = text.replace(old, "")

    script = '<script type="module" src="js/profile-role-v14.js"></script>'
    if "</body>" in text:
        text = text.replace("</body>", f"{script}\n</body>", 1)
    else:
        text += "\n" + script + "\n"

    p.write_text(text, encoding="utf-8")
    print("OK patched frontend/profile.html")


def main() -> None:
    root = Path.cwd()
    patch_root = Path(__file__).resolve().parent
    if not (root / "app").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto backend/frontend.")
    copy_files(root, patch_root)
    patch_main(root)
    patch_profile_html(root)
    print("\nPatch v14 installata.")
    print("Ora deploya il backend su Render e carica i file frontend su SiteGround.")
    print("Poi imposta ADMIN_BOOTSTRAP_TOKEN su Render e usa /docs -> /admin-bootstrap/promote-me.")


if __name__ == "__main__":
    main()
