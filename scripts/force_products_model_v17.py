from __future__ import annotations

import re
import shutil
from pathlib import Path


PRODUCT_FIELDS = [
    "brand = Column(String, nullable=True)",
    "flyer_page = Column(Integer, nullable=True)",
    "flyer_valid_from = Column(String, nullable=True)",
    "flyer_valid_to = Column(String, nullable=True)",
    "flyer_source = Column(String, nullable=True)",
    "flyer_source_url = Column(Text, nullable=True)",
    "is_lidl_plus = Column(Boolean, default=False)",
    "flyer_imported_at = Column(String, nullable=True)",
    "offer_note = Column(Text, nullable=True)",
    "discount_percent = Column(Float, nullable=True)",
]


def ensure_text_import(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("from sqlalchemy import "):
            imports = [item.strip() for item in line.replace("from sqlalchemy import ", "").split(",")]
            if "Text" not in imports:
                imports.append("Text")
            new_line = "from sqlalchemy import " + ", ".join(dict.fromkeys(imports))
            return text.replace(line, new_line, 1)

    return "from sqlalchemy import Text\n" + text


def find_class_block(text: str, class_name: str) -> tuple[int, int]:
    pattern = re.compile(rf"^class {re.escape(class_name)}\b.*?:\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        raise RuntimeError(f"Non trovo class {class_name} in app/models.py")

    start = match.start()
    next_class = re.search(r"^class \w+\b.*?:\s*$", text[match.end():], re.MULTILINE)
    if next_class:
        end = match.end() + next_class.start()
    else:
        end = len(text)

    return start, end


def patch_products_block(block: str) -> str:
    existing = block

    missing = [field for field in PRODUCT_FIELDS if field.split(" = ", 1)[0] not in existing]
    if not missing:
        return block

    addition = "\n".join(f"    {field}" for field in missing)

    preferred_anchors = [
        "    location = Column(String, nullable=True)",
        "    protein = Column(Float, nullable=True)",
        "    aisle_order = Column(Float",
        "    aisle_order = Column(Integer",
        "    unit = Column(String",
    ]

    lines = block.splitlines()
    insert_idx = None

    for anchor in preferred_anchors:
        for i, line in enumerate(lines):
            if line.strip().startswith(anchor.strip()):
                insert_idx = i + 1
        if insert_idx is not None:
            break

    if insert_idx is None:
        for i, line in enumerate(lines):
            if "relationship(" in line:
                insert_idx = i
                break

    if insert_idx is None:
        insert_idx = len(lines)

    lines.insert(insert_idx, addition)
    return "\n".join(lines)


def patch_models_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    text = ensure_text_import(original)

    start, end = find_class_block(text, "Products")
    before, block, after = text[:start], text[start:end], text[end:]
    new_block = patch_products_block(block)
    new_text = before + new_block + after

    if new_text == original:
        return False

    backup = path.with_suffix(".py.bak_force_products_model_v17")
    if not backup.exists():
        shutil.copy2(path, backup)

    path.write_text(new_text, encoding="utf-8")
    return True


def verify(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    start, end = find_class_block(text, "Products")
    block = text[start:end]

    required = [
        "brand = Column",
        "flyer_page = Column",
        "flyer_valid_from = Column",
        "flyer_valid_to = Column",
        "is_lidl_plus = Column",
        "offer_note = Column",
        "discount_percent = Column",
    ]

    missing = [item for item in required if item not in block]
    print("\nVerifica Products model:")
    if missing:
        print("MANCANO ancora:")
        for item in missing:
            print(f"- {item}")
        raise SystemExit(1)

    print("OK: Products contiene brand/flyer fields.")
    print("\nOra devi fare commit/push/deploy su Render.")
    print("Dopo il deploy, Swagger GET /admin/debug/products-model deve dare has_brand=true.")


def main() -> None:
    root = Path.cwd()
    models_path = root / "app" / "models.py"

    if not models_path.exists():
        raise RuntimeError("Non trovo app/models.py. Devi eseguire lo script dalla root del progetto.")

    changed = patch_models_file(models_path)
    print("app/models.py aggiornato." if changed else "app/models.py era già aggiornato.")
    verify(models_path)


if __name__ == "__main__":
    main()
