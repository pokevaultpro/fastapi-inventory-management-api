from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from app.database import Base, engine
    import app.models  # noqa
    from app.services.flyer_offer_schema import ensure_flyer_offer_schema, schema_debug

    Base.metadata.create_all(bind=engine)
    ensure_flyer_offer_schema(engine)
    debug = schema_debug(engine)

    print("OK Flyer Offers schema ready.")
    for table, columns in debug.items():
        print(f"{table}: {len(columns)} columns")


if __name__ == "__main__":
    main()
