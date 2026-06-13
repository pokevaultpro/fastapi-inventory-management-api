# SmartGrocery v21 — Ricette con description, instructions, servings, prep_time_minutes

## Problema

Le ricette continuavano a non salvare/mostrare:

```txt
description
instructions
servings
prep_time_minutes
```

Perché il fix precedente non era stato installato e nel frattempo il progetto è andato avanti con altre patch.

## Cosa fa questa patch

- aggiorna `app/models.py` con:
  - `Recipes.description`
  - `Recipes.instructions`
  - `Recipes.servings`
  - `Recipes.prep_time_minutes`
  - `Recipes.source_type`
  - `Recipes.source_url`
  - `Recipes.estimated_total`
  - `Recipes.created_at`
- aggiorna anche `RecipeItems` con:
  - `amount`
  - `amount_unit`
  - `note`
  - `is_optional`
  - `cart_quantity`
  - `snapshot_price`
- aggiorna `/smart-recipes`;
- aggiorna pagina ricette frontend per mostrare descrizione e istruzioni;
- conserva le colonne v20 per prodotti al peso/prezzo manuale dentro `schema_compat.py`.

## Installazione

Dalla root del progetto:

```powershell
python install_recipes_fields_v21.py
python scripts\force_recipes_fields_v21.py
```

Poi fai commit/push/deploy su Render.

## Se Render non crea le colonne DB

Normalmente `ensure_schema_compat(engine)` lo fa all'avvio.

Se serve, da Render shell:

```bash
python scripts/migrate_recipes_fields_v21.py
```

## Controllo dopo deploy

In Swagger online:

```txt
GET /smart-recipes/debug/model
```

Deve dare:

```json
{
  "has_description": true,
  "has_instructions": true,
  "has_servings": true,
  "has_prep_time_minutes": true
}
```

## Frontend SiteGround

Carica:

```txt
frontend/js/recipes.js
frontend/css/recipes.css
```

Poi fai Ctrl+F5.

## Nota importante

Le ricette già salvate senza descrizione/istruzioni potrebbero avere quei campi vuoti.
Dopo il fix, apri la ricetta, modifica descrizione/istruzioni/porzioni/tempo e salva.
