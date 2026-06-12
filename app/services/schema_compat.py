from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


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
}

RECIPE_METADATA_COLUMNS = {
    "description": "TEXT",
    "servings": "INTEGER DEFAULT 1",
    "prep_time_minutes": "INTEGER",
    "instructions": "TEXT",
    "source_type": "VARCHAR(40) DEFAULT 'personal'",
    "source_url": "TEXT",
    "estimated_total": "FLOAT",
    "created_at": "VARCHAR(40)",
}

RECIPE_ITEM_METADATA_COLUMNS = {
    "amount": "FLOAT",
    "amount_unit": "VARCHAR(40)",
    "note": "TEXT",
    "is_optional": "BOOLEAN DEFAULT FALSE",
    "cart_quantity": "INTEGER DEFAULT 1",
    "snapshot_price": "FLOAT",
}


def _add_missing_columns(engine: Engine, table_name: str, wanted: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table_name not in set(inspector.get_table_names()):
        return
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    missing = [name for name in wanted if name not in existing]
    if not missing:
        return
    with engine.begin() as connection:
        for column_name in missing:
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {wanted[column_name]}"))


def ensure_product_metadata_columns(engine: Engine) -> None:
    _add_missing_columns(engine, "products", PRODUCT_METADATA_COLUMNS)


def ensure_recipe_metadata_columns(engine: Engine) -> None:
    _add_missing_columns(engine, "recipes", RECIPE_METADATA_COLUMNS)
    _add_missing_columns(engine, "recipe_items", RECIPE_ITEM_METADATA_COLUMNS)


def ensure_schema_compat(engine: Engine) -> None:
    """Small non-destructive migrations for older local/Render databases."""
    ensure_product_metadata_columns(engine)
    ensure_recipe_metadata_columns(engine)
