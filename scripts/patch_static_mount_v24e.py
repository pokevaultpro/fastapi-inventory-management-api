from __future__ import annotations

import shutil
from pathlib import Path


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


def main() -> None:
    root = Path.cwd()
    path = root / "app" / "main.py"

    if not path.exists():
        raise RuntimeError("Non trovo app/main.py. Esegui dalla root del progetto.")

    backup = path.with_suffix(".py.bak_flyer_static_v24e")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")

    text = ensure_import(text, "from pathlib import Path")
    text = ensure_import(text, "from fastapi.staticfiles import StaticFiles")

    static_block = (
        "\n# Static files: product images and flyer extracted pages\n"
        "Path('static').mkdir(parents=True, exist_ok=True)\n"
        "if not any(getattr(route, 'path', None) == '/static' for route in app.routes):\n"
        "    app.mount('/static', StaticFiles(directory='static'), name='static')\n"
    )

    if "app.mount('/static'" not in text and 'app.mount("/static"' not in text:
        marker = "app.add_middleware("
        idx = text.find(marker)
        if idx != -1:
            # Insert before middleware/app routes, after app = FastAPI() and exception handler area.
            # Safer: after CORS middleware block if Base.metadata exists.
            base_marker = "Base.metadata.create_all(bind=engine)"
            if base_marker in text:
                text = text.replace(base_marker, static_block + "\n" + base_marker, 1)
            else:
                text = text.replace(marker, static_block + "\n" + marker, 1)
        else:
            text += "\n" + static_block + "\n"

    path.write_text(text, encoding="utf-8")
    print("OK app/main.py: /static montato per immagini volantini.")


if __name__ == "__main__":
    main()
