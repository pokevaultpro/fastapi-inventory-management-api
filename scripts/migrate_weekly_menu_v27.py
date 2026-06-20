from __future__ import annotations

from app.routers.weekly_menus import ensure_schema_ready

if __name__ == "__main__":
    ensure_schema_ready()
    print("OK: weekly_menus multi-ricetta pronto.")
