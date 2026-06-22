from __future__ import annotations

from app.routers.recipe_smart import ensure_recipe_nutrition_schema

if __name__ == "__main__":
    ensure_recipe_nutrition_schema()
    print("OK: tabella recipe_nutrition pronta.")
