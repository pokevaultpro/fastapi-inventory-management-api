from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import inspect, text


PRODUCT_COLUMNS = {
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


def safe_db_label(url: str | None) -> str:
    if not url:
        return "DATABASE_URL non impostato"
    if "@" not in url:
        return url
    prefix, rest = url.split("@", 1)
    scheme = prefix.split("://", 1)[0] if "://" in prefix else "database"
    return f"{scheme}://***:***@{rest}"


def add_missing_columns(engine, table_name: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    if table_name not in table_names:
        print(f"SKIP {table_name}: tabella non trovata")
        return

    existing = {col["name"] for col in inspector.get_columns(table_name)}
    missing = [(name, ddl) for name, ddl in columns.items() if name not in existing]

    if not missing:
        print(f"OK {table_name}: nessuna colonna mancante")
        return

    with engine.begin() as connection:
        for name, ddl in missing:
            print(f"ADD {table_name}.{name}")
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl}"))


def main() -> None:
    print("SmartGrocery DB migration v9")
    print("-" * 40)

    try:
        from app.database import Base, engine
        import app.models  # noqa: F401 - needed so SQLAlchemy sees all models
    except Exception as exc:
        print("ERRORE: non riesco a importare app.database/app.models.")
        print("Assicurati di lanciare questo script dalla root del progetto.")
        print(f"Dettaglio: {exc}")
        raise

    db_url = os.getenv("DATABASE_URL")
    print(f"Database target: {safe_db_label(db_url)}")

    print("\n1) Creo eventuali tabelle mancanti...")
    Base.metadata.create_all(bind=engine)

    print("\n2) Aggiungo colonne mancanti...")
    add_missing_columns(engine, "products", PRODUCT_COLUMNS)
    add_missing_columns(engine, "recipes", RECIPE_COLUMNS)
    add_missing_columns(engine, "recipe_items", RECIPE_ITEM_COLUMNS)

    print("\n3) Verifica finale...")
    inspector = inspect(engine)
    for table in ["users", "products", "cart", "shopping_history", "recipes", "recipe_items"]:
        exists = table in set(inspector.get_table_names())
        print(f"{'OK' if exists else 'MISSING'} table {table}")

    print("\nMigrazione completata.")
    print("Ora riavvia FastAPI e fai Ctrl+F5 nel browser.")


if __name__ == "__main__":
    main()
