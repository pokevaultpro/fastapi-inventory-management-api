from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from app.database import Base, engine
    import app.models  # noqa
    from app.services.schema_compat import ensure_schema_compat

    print("Creating missing tables, then adding variable pricing columns...")
    Base.metadata.create_all(bind=engine)
    ensure_schema_compat(engine)
    print("OK variable pricing schema ready.")


if __name__ == "__main__":
    main()
