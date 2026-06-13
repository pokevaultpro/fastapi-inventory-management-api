from __future__ import annotations

import py_compile
import re
import shutil
from pathlib import Path


FIELDS = [
    "brand = Column(String, nullable=True)",
    "price_type = Column(String, default=\"fixed\")",
    "price_unit = Column(String, nullable=True)",
    "flyer_page = Column(Integer, nullable=True)",
    "flyer_valid_from = Column(String, nullable=True)",
    "flyer_valid_to = Column(String, nullable=True)",
    "flyer_source = Column(Text, nullable=True)",
    "flyer_source_url = Column(Text, nullable=True)",
    "is_lidl_plus = Column(Boolean, default=False)",
    "offer_note = Column(Text, nullable=True)",
    "discount_percent = Column(Float, nullable=True)",
]


def ensure_import(text: str, imported: str) -> str:
    for line in text.splitlines():
        if line.startswith("from sqlalchemy import "):
            parts = [p.strip() for p in line.replace("from sqlalchemy import ", "").split(",")]
            if imported not in parts:
                parts.append(imported)
            return text.replace(line, "from sqlalchemy import " + ", ".join(dict.fromkeys(parts)), 1)
    return f"from sqlalchemy import {imported}\n" + text


def find_class_block(text: str, class_name: str) -> tuple[int, int]:
    match = re.search(rf"^class {class_name}\b.*?:\s*$", text, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Non trovo class {class_name}")
    start = match.start()
    next_match = re.search(r"^class \w+\b.*?:\s*$", text[match.end():], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(text)
    return start, end


def patch_products(text: str) -> str:
    start, end = find_class_block(text, "Products")
    block = text[start:end]
    missing = [field for field in FIELDS if field.split(" = ", 1)[0] not in block]
    if not missing:
        return text

    lines = block.splitlines()
    insert_idx = None
    for i, line in enumerate(lines):
        if "location = Column" in line or "protein = Column" in line or "image = Column" in line:
            insert_idx = i + 1
    if insert_idx is None:
        insert_idx = len(lines)

    lines.insert(insert_idx, "\n".join(f"    {field}" for field in missing))
    new_block = "\n".join(lines)
    return text[:start] + new_block + text[end:]


def main() -> None:
    root = Path.cwd()
    path = root / "app" / "models.py"
    if not path.exists():
        raise RuntimeError("Non trovo app/models.py")

    original = path.read_text(encoding="utf-8")
    text = original
    for imp in ["Text", "Boolean"]:
        text = ensure_import(text, imp)

    text = patch_products(text)
    text = re.sub(r"(\))class\s+", r"\1\n\nclass ", text)

    if text != original:
        backup = path.with_suffix(".py.bak_flyer_products_v26")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(text, encoding="utf-8")
        print("OK app/models.py Products aggiornato con campi flyer.")
    else:
        print("app/models.py era già aggiornato.")

    py_compile.compile(str(path), doraise=True)
    print("OK compile app/models.py")


if __name__ == "__main__":
    main()
