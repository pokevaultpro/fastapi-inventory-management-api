from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


PRODUCT_EXTRA_COLUMNS = {
    "brand": "TEXT",
    "price_type": "VARCHAR(20) DEFAULT 'fixed'",
    "price_unit": "VARCHAR(20)",
    "flyer_page": "INTEGER",
    "flyer_valid_from": "VARCHAR(20)",
    "flyer_valid_to": "VARCHAR(20)",
    "flyer_source": "TEXT",
    "flyer_source_url": "TEXT",
    "is_lidl_plus": "BOOLEAN DEFAULT FALSE",
    "offer_note": "TEXT",
    "discount_percent": "FLOAT",
}


def dialect_name(engine: Engine) -> str:
    return engine.dialect.name.lower()


def table_exists(engine: Engine, table_name: str) -> bool:
    return inspect(engine).has_table(table_name)


def get_columns(engine: Engine, table_name: str) -> set[str]:
    if not table_exists(engine, table_name):
        return set()
    return {column["name"] for column in inspect(engine).get_columns(table_name)}


def execute_ddl(engine: Engine, sql: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(sql))


def add_column_if_missing(engine: Engine, table_name: str, column_name: str, definition: str) -> None:
    if column_name in get_columns(engine, table_name):
        return

    if dialect_name(engine) == "postgresql":
        execute_ddl(engine, f'ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {definition}')
    else:
        execute_ddl(engine, f'ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}')


def ensure_product_extra_columns(engine: Engine) -> None:
    if not table_exists(engine, "products"):
        return

    for column, definition in PRODUCT_EXTRA_COLUMNS.items():
        try:
            add_column_if_missing(engine, "products", column, definition)
        except Exception:
            # Avoid blocking the whole app if a column exists with a slightly different type.
            pass


def ensure_flyer_offer_schema(engine: Engine) -> None:
    name = dialect_name(engine)
    ensure_product_extra_columns(engine)

    if name == "postgresql":
        execute_ddl(engine, """
        CREATE TABLE IF NOT EXISTS flyers (
            id SERIAL PRIMARY KEY,
            supermarket_id INTEGER,
            retailer VARCHAR(150) NOT NULL,
            title TEXT,
            valid_from VARCHAR(20),
            valid_to VARCHAR(20),
            source TEXT,
            source_url TEXT,
            status VARCHAR(30) DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        execute_ddl(engine, """
        CREATE TABLE IF NOT EXISTS flyer_offers (
            id SERIAL PRIMARY KEY,
            flyer_id INTEGER NOT NULL REFERENCES flyers(id) ON DELETE CASCADE,
            product_id INTEGER NULL,
            suggested_product_id INTEGER NULL,
            raw_name TEXT NOT NULL,
            normalized_name TEXT,
            brand TEXT,
            category TEXT,
            unit TEXT,
            offer_price FLOAT NOT NULL,
            original_price FLOAT NULL,
            price_type VARCHAR(20) DEFAULT 'fixed',
            price_unit VARCHAR(20),
            flyer_page INTEGER,
            image TEXT,
            valid_from VARCHAR(20),
            valid_to VARCHAR(20),
            source TEXT,
            source_url TEXT,
            is_loyalty_only BOOLEAN DEFAULT FALSE,
            is_from_price BOOLEAN DEFAULT FALSE,
            offer_note TEXT,
            match_status VARCHAR(40) DEFAULT 'needs_review',
            match_score FLOAT DEFAULT 0,
            status VARCHAR(40) DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        execute_ddl(engine, """
        CREATE TABLE IF NOT EXISTS product_aliases (
            id SERIAL PRIMARY KEY,
            supermarket_id INTEGER,
            product_id INTEGER NOT NULL,
            alias_name TEXT NOT NULL,
            normalized_alias TEXT NOT NULL,
            confidence FLOAT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        execute_ddl(engine, "CREATE INDEX IF NOT EXISTS idx_flyer_offers_flyer_id ON flyer_offers(flyer_id)")
        execute_ddl(engine, "CREATE INDEX IF NOT EXISTS idx_flyer_offers_product_id ON flyer_offers(product_id)")
        execute_ddl(engine, "CREATE INDEX IF NOT EXISTS idx_flyer_offers_status ON flyer_offers(status)")
        execute_ddl(engine, "CREATE INDEX IF NOT EXISTS idx_product_aliases_norm ON product_aliases(normalized_alias)")

    else:
        execute_ddl(engine, """
        CREATE TABLE IF NOT EXISTS flyers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supermarket_id INTEGER,
            retailer VARCHAR(150) NOT NULL,
            title TEXT,
            valid_from VARCHAR(20),
            valid_to VARCHAR(20),
            source TEXT,
            source_url TEXT,
            status VARCHAR(30) DEFAULT 'draft',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        execute_ddl(engine, """
        CREATE TABLE IF NOT EXISTS flyer_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flyer_id INTEGER NOT NULL,
            product_id INTEGER NULL,
            suggested_product_id INTEGER NULL,
            raw_name TEXT NOT NULL,
            normalized_name TEXT,
            brand TEXT,
            category TEXT,
            unit TEXT,
            offer_price FLOAT NOT NULL,
            original_price FLOAT NULL,
            price_type VARCHAR(20) DEFAULT 'fixed',
            price_unit VARCHAR(20),
            flyer_page INTEGER,
            image TEXT,
            valid_from VARCHAR(20),
            valid_to VARCHAR(20),
            source TEXT,
            source_url TEXT,
            is_loyalty_only BOOLEAN DEFAULT FALSE,
            is_from_price BOOLEAN DEFAULT FALSE,
            offer_note TEXT,
            match_status VARCHAR(40) DEFAULT 'needs_review',
            match_score FLOAT DEFAULT 0,
            status VARCHAR(40) DEFAULT 'draft',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        execute_ddl(engine, """
        CREATE TABLE IF NOT EXISTS product_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supermarket_id INTEGER,
            product_id INTEGER NOT NULL,
            alias_name TEXT NOT NULL,
            normalized_alias TEXT NOT NULL,
            confidence FLOAT DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

    # Columns added after first drafts; useful if table already existed.
    for table, columns in {
        "flyers": {
            "supermarket_id": "INTEGER",
            "source_url": "TEXT",
            "updated_at": "VARCHAR(40)",
        },
        "flyer_offers": {
            "suggested_product_id": "INTEGER",
            "original_price": "FLOAT",
            "source_url": "TEXT",
            "is_from_price": "BOOLEAN DEFAULT FALSE",
            "match_score": "FLOAT DEFAULT 0",
            "updated_at": "VARCHAR(40)",
        },
        "product_aliases": {
            "supermarket_id": "INTEGER",
            "confidence": "FLOAT DEFAULT 1",
        },
    }.items():
        for column, definition in columns.items():
            try:
                add_column_if_missing(engine, table, column, definition)
            except Exception:
                pass


def schema_debug(engine: Engine) -> dict:
    ensure_flyer_offer_schema(engine)
    return {
        "products": sorted(get_columns(engine, "products")),
        "flyers": sorted(get_columns(engine, "flyers")),
        "flyer_offers": sorted(get_columns(engine, "flyer_offers")),
        "product_aliases": sorted(get_columns(engine, "product_aliases")),
    }
