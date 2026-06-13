from __future__ import annotations

import py_compile
import re
import shutil
from pathlib import Path


RECIPE_FIELDS = [
    "description = Column(Text, nullable=True)",
    "servings = Column(Integer, default=1)",
    "prep_time_minutes = Column(Integer, nullable=True)",
    "instructions = Column(Text, nullable=True)",
    "source_type = Column(String, default=\"personal\")",
    "source_url = Column(Text, nullable=True)",
    "estimated_total = Column(Float, nullable=True)",
    "created_at = Column(String, nullable=True)",
]

RECIPE_ITEM_FIELDS = [
    "amount = Column(Float, nullable=True)",
    "amount_unit = Column(String, nullable=True)",
    "note = Column(Text, nullable=True)",
    "is_optional = Column(Boolean, default=False)",
    "cart_quantity = Column(Integer, default=1)",
    "snapshot_price = Column(Float, nullable=True)",
]


def fix_glued_classes(text: str) -> str:
    # Safety: fixes accidental "... )class Next(Base):" patterns.
    text = re.sub(r'(\))class\s+', r'\1\n\nclass ', text)
    text = re.sub(r'([A-Za-z0-9_"\')\]])class\s+', r'\1\n\nclass ', text)
    return text


def ensure_sqlalchemy_imports(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("from sqlalchemy import "):
            imports = [item.strip() for item in line.replace("from sqlalchemy import ", "").split(",")]
            for needed in ["Text"]:
                if needed not in imports:
                    imports.append(needed)
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
    end = match.end() + next_class.start() if next_class else len(text)
    return start, end


def class_block(text: str, class_name: str) -> str:
    start, end = find_class_block(text, class_name)
    return text[start:end]


def insert_fields(block: str, fields: list[str], anchors: list[str]) -> str:
    missing = [field for field in fields if field.split(" = ", 1)[0] not in block]
    if not missing:
        return block

    addition = "\n".join(f"    {field}" for field in missing)
    lines = block.splitlines()
    insert_idx = None

    for anchor in anchors:
        for i, line in enumerate(lines):
            if line.strip().startswith(anchor):
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


def patch_class(text: str, class_name: str, fields: list[str], anchors: list[str]) -> str:
    start, end = find_class_block(text, class_name)
    block = text[start:end]
    new_block = insert_fields(block, fields, anchors)
    return text[:start] + new_block + text[end:]


def main() -> None:
    root = Path.cwd()
    path = root / "app" / "models.py"

    if not path.exists():
        raise RuntimeError("Non trovo app/models.py. Esegui dalla root del progetto.")

    original = path.read_text(encoding="utf-8")
    text = fix_glued_classes(original)
    text = ensure_sqlalchemy_imports(text)

    text = patch_class(text, "Recipes", RECIPE_FIELDS, [
        "created_at = Column",
        "estimated_total = Column",
        "image = Column",
        "owner_id = Column",
        "name = Column",
    ])

    text = patch_class(text, "RecipeItems", RECIPE_ITEM_FIELDS, [
        "snapshot_price = Column",
        "cart_quantity = Column",
        "amount = Column",
        "quantity = Column",
        "product_id = Column",
        "recipe_id = Column",
    ])

    if text != original:
        backup = path.with_suffix(".py.bak_recipes_fields_v21")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(text, encoding="utf-8")
        print("OK app/models.py aggiornato.")
    else:
        print("app/models.py era già aggiornato.")

    py_compile.compile(str(path), doraise=True)
    print("OK compile: app/models.py")

    updated = path.read_text(encoding="utf-8")
    recipes = class_block(updated, "Recipes")
    recipe_items = class_block(updated, "RecipeItems")

    checks = {
        "Recipes.description": "description = Column" in recipes,
        "Recipes.instructions": "instructions = Column" in recipes,
        "Recipes.servings": "servings = Column" in recipes,
        "Recipes.prep_time_minutes": "prep_time_minutes = Column" in recipes,
        "RecipeItems.amount": "amount = Column" in recipe_items,
        "RecipeItems.cart_quantity": "cart_quantity = Column" in recipe_items,
        "RecipeItems.snapshot_price": "snapshot_price = Column" in recipe_items,
    }

    print("\nVerifica recipe model:")
    for key, ok in checks.items():
        print(f"{'OK' if ok else 'MISSING'} {key}")

    if not all(checks.values()):
        raise SystemExit(1)

    for rel in [
        "app/routers/recipe_smart.py",
        "app/routers/admin.py",
        "app/services/schema_compat.py",
    ]:
        p = root / rel
        if p.exists():
            py_compile.compile(str(p), doraise=True)
            print(f"OK compile: {rel}")

    print("\nOK: ricette pronte lato model.")
    print("Ora fai commit/push/deploy su Render.")
    print("Dopo il deploy controlla GET /smart-recipes/debug/model.")


if __name__ == "__main__":
    main()
