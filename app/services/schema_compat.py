from __future__ import annotations

from sqlalchemy import inspect, text


PRODUCT_METADATA_COLUMNS = {
    "brand": "VARCHAR(120)",
    "flyer_page": "INTEGER",
    "flyer_valid_from": "VARCHAR(32)",
    "flyer_valid_to": "VARCHAR(32)",
    "flyer_source": "VARCHAR(180)",
    "flyer_source_url": "TEXT",
    "is_lidl_plus": "BOOLEAN DEFAULT FALSE",
    "flyer_imported_at": "VARCHAR(40)",
    "offer_note": "TEXT",
    "discount_percent": "FLOAT",
    "price_type": "VARCHAR(20) DEFAULT 'fixed'",
    "price_unit": "VARCHAR(20)",
}

CART_VARIABLE_PRICE_COLUMNS = {
    "estimated_weight": "FLOAT",
    "actual_weight": "FLOAT",
    "manual_price": "FLOAT",
}

SHOPPING_HISTORY_VARIABLE_PRICE_COLUMNS = {
    "price_type": "VARCHAR(20)",
    "price_unit": "VARCHAR(20)",
    "estimated_weight": "FLOAT",
    "actual_weight": "FLOAT",
    "weight_bought": "FLOAT",
    "price_per_unit_snapshot": "FLOAT",
    "final_price_paid": "FLOAT",
    "was_manual_price": "BOOLEAN DEFAULT FALSE",
    "manual_price": "FLOAT",
}

RECIPE_COLUMNS = {
    "description": "TEXT",
    "servings": "INTEGER DEFAULT 1",
    "prep_time_minutes": "INTEGER",
    "instructions": "TEXT",
    "source_type": "VARCHAR(40) DEFAULT 'personal'",
    "source_url": "TEXT",
    "estimated_total": "FLOAT",
    "created_at": "VARCHAR(40)",
}

RECIPE_ITEM_COLUMNS = {
    "amount": "FLOAT",
    "amount_unit": "VARCHAR(40)",
    "note": "TEXT",
    "is_optional": "BOOLEAN DEFAULT FALSE",
    "cart_quantity": "INTEGER DEFAULT 1",
    "snapshot_price": "FLOAT",
}


def add_missing_columns(engine, table_name: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table_name not in set(inspector.get_table_names()):
        return

    existing = {col["name"] for col in inspector.get_columns(table_name)}
    missing = [(name, ddl) for name, ddl in columns.items() if name not in existing]

    if not missing:
        return

    with engine.begin() as connection:
        for name, ddl in missing:
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl}"))


def ensure_product_metadata_columns(engine) -> None:
    add_missing_columns(engine, "products", PRODUCT_METADATA_COLUMNS)


def ensure_schema_compat(engine) -> None:
    add_missing_columns(engine, "products", PRODUCT_METADATA_COLUMNS)
    add_missing_columns(engine, "cart", CART_VARIABLE_PRICE_COLUMNS)
    add_missing_columns(engine, "shopping_history_items", SHOPPING_HISTORY_VARIABLE_PRICE_COLUMNS)
    add_missing_columns(engine, "recipes", RECIPE_COLUMNS)
    add_missing_columns(engine, "recipe_items", RECIPE_ITEM_COLUMNS)
