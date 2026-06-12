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


def ensure_product_metadata_columns(engine: Engine) -> None:
    """
    Adds optional flyer/catalog metadata columns to the existing products table.

    Why this exists:
    - Base.metadata.create_all() creates missing tables, but does not add new columns
      to an existing table.
    - This project is deployed both locally and online, so this small compatibility
      step lets older databases receive the new non-breaking columns automatically.

    The columns are nullable and safe for existing products.
    """
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "products" not in table_names:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("products")}
    missing = [name for name in PRODUCT_METADATA_COLUMNS if name not in existing_columns]
    if not missing:
        return

    with engine.begin() as connection:
        for column_name in missing:
            column_type = PRODUCT_METADATA_COLUMNS[column_name]
            connection.execute(text(f"ALTER TABLE products ADD COLUMN {column_name} {column_type}"))
