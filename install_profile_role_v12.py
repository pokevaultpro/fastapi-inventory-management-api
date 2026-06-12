from __future__ import annotations

import shutil
from pathlib import Path


PATCH_FILES = [
    "app/routers/profile_role.py",
    "frontend/js/profile-role-badge.js",
    "docs/PROFILE_ROLE_V12.md",
]


def copy_patch_files(project_root: Path, patch_root: Path) -> None:
    for rel in PATCH_FILES:
        src = patch_root / rel
        dst = project_root / rel
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


def patch_main_py(project_root: Path) -> None:
    main_path = project_root / "app" / "main.py"
    if not main_path.exists():
        raise FileNotFoundError("Non trovo app/main.py")

    backup = main_path.with_suffix(".py.bak_profile_role_v12")
    if not backup.exists():
        shutil.copy2(main_path, backup)
        print(f"Backup creato: {backup}")

    text = main_path.read_text(encoding="utf-8")
    text = ensure_import(text, "from app.routers import profile_role")

    include_line = "app.include_router(profile_role.router)"
    if include_line not in text:
        text = text.rstrip() + "\n" + include_line + "\n"

    main_path.write_text(text, encoding="utf-8")
    print("OK patched app/main.py")


def patch_profile_html(project_root: Path) -> None:
    profile_path = project_root / "frontend" / "profile.html"
    if not profile_path.exists():
        raise FileNotFoundError("Non trovo frontend/profile.html")

    backup = profile_path.with_suffix(".html.bak_profile_role_v12")
    if not backup.exists():
        shutil.copy2(profile_path, backup)
        print(f"Backup creato: {backup}")

    text = profile_path.read_text(encoding="utf-8")
    script = '<script type="module" src="js/profile-role-badge.js"></script>'

    if "profile-role-badge.js" not in text:
        if "</body>" in text:
            text = text.replace("</body>", f"{script}\n</body>", 1)
        else:
            text += "\n" + script + "\n"

    profile_path.write_text(text, encoding="utf-8")
    print("OK patched frontend/profile.html")


def main() -> None:
    project_root = Path.cwd()
    patch_root = Path(__file__).resolve().parent

    if not (project_root / "app").exists() or not (project_root / "frontend").exists():
        raise RuntimeError("Estrai lo ZIP nella root del progetto, poi esegui python install_profile_role_v12.py")

    copy_patch_files(project_root, patch_root)
    patch_main_py(project_root)
    patch_profile_html(project_root)

    print()
    print("Patch v12 installata.")
    print("Riavvia uvicorn, fai logout/login se hai appena cambiato ruolo, poi Ctrl+F5 su profile.html.")


if __name__ == "__main__":
    main()
