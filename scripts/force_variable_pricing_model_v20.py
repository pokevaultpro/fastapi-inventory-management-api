from __future__ import annotations

import re
import shutil
from pathlib import Path


PRODUCT_FIELDS = [
    "price_type = Column(String, default=\"fixed\")",
    "price_unit = Column(String, nullable=True)",
]

CART_FIELDS = [
    "estimated_weight = Column(Float, nullable=True)",
    "actual_weight = Column(Float, nullable=True)",
    "manual_price = Column(Float, nullable=True)",
]

HISTORY_ITEM_FIELDS = [
    "price_type = Column(String, nullable=True)",
    "price_unit = Column(String, nullable=True)",
    "estimated_weight = Column(Float, nullable=True)",
    "actual_weight = Column(Float, nullable=True)",
    "weight_bought = Column(Float, nullable=True)",
    "price_per_unit_snapshot = Column(Float, nullable=True)",
    "final_price_paid = Column(Float, nullable=True)",
    "was_manual_price = Column(Boolean, default=False)",
    "manual_price = Column(Float, nullable=True)",
]


def find_class_block(text: str, class_name: str) -> tuple[int, int]:
    pattern = re.compile(rf"^class {re.escape(class_name)}\b.*?:\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        raise RuntimeError(f"Non trovo class {class_name} in app/models.py")
    start = match.start()
    next_class = re.search(r"^class \w+\b.*?:\s*$", text[match.end():], re.MULTILINE)
    end = match.end() + next_class.start() if next_class else len(text)
    return start, end


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
    text = original

    text = patch_class(text, "Products", PRODUCT_FIELDS, ["discount_percent = Column", "offer_note = Column", "location = Column", "protein = Column"])
    text = patch_class(text, "Cart", CART_FIELDS, ["checked = Column", "owner_id = Column", "quantity = Column"])
    text = patch_class(text, "ShoppingHistoryItem", HISTORY_ITEM_FIELDS, ["protein = Column", "supermarket_name = Column", "quantity = Column"])

    if text != original:
        backup = path.with_suffix(".py.bak_variable_pricing_v20")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(text, encoding="utf-8")
        print("OK app/models.py aggiornato.")
    else:
        print("app/models.py era già aggiornato.")

    updated = path.read_text(encoding="utf-8")
    checks = {
        "Products.price_type": "price_type = Column" in updated[find_class_block(updated, "Products")[0]:find_class_block(updated, "Products")[1]],
        "Products.price_unit": "price_unit = Column" in updated[find_class_block(updated, "Products")[0]:find_class_block(updated, "Products")[1]],
        "Cart.estimated_weight": "estimated_weight = Column" in updated[find_class_block(updated, "Cart")[0]:find_class_block(updated, "Cart")[1]],
        "Cart.manual_price": "manual_price = Column" in updated[find_class_block(updated, "Cart")[0]:find_class_block(updated, "Cart")[1]],
        "ShoppingHistoryItem.weight_bought": "weight_bought = Column" in updated[find_class_block(updated, "ShoppingHistoryItem")[0]:find_class_block(updated, "ShoppingHistoryItem")[1]],
        "ShoppingHistoryItem.final_price_paid": "final_price_paid = Column" in updated[find_class_block(updated, "ShoppingHistoryItem")[0]:find_class_block(updated, "ShoppingHistoryItem")[1]],
    }

    print("\nVerifica model:")
    for key, ok in checks.items():
        print(f"{'OK' if ok else 'MISSING'} {key}")

    if not all(checks.values()):
        raise SystemExit(1)

    print("\nOra fai deploy su Render.")
    print("Poi controlla che il carrello salvi estimated_weight/manual_price senza errori.")


if __name__ == "__main__":
    main()
