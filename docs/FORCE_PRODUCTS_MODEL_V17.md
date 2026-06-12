# SmartGrocery v17 — Force patch Products model

Il tuo debug online dice:

```json
"has_brand": false,
"has_flyer_valid_from": false
```

Questo significa che Render sta usando un `app/models.py` in cui `class Products` non contiene ancora i nuovi campi.

Questa patch forza l'aggiunta dei campi mancanti dentro `class Products`.

## Installazione locale

Dalla root del progetto:

```powershell
python install_force_products_model_v17.py
python scripts\force_products_model_v17.py
```

Lo script deve stampare:

```txt
OK: Products contiene brand/flyer fields.
```

## Poi devi deployare su Render

Il fix non arriva online finché non fai deploy del backend aggiornato.

Dopo il deploy:

```txt
GET /admin/debug/products-model
```

Deve dare:

```json
"has_brand": true,
"has_flyer_valid_from": true
```

## Importante

Se hai già fatto deploy ma continua `false`, allora Render sta deployando da un branch/repo diverso oppure il commit non contiene `app/models.py` modificato.
