# SmartGrocery v16 — Fix admin product backend

## Errore risolto

Traceback:

```txt
TypeError: 'brand' is an invalid keyword argument for Products
```

Causa: il backend admin riceveva campi nuovi (`brand`, `flyer_page`, ecc.), ma il modello SQLAlchemy `Products` deployato su Render era ancora quello vecchio e non conosceva `brand`.

## Cosa fa questa patch

- aggiorna `app/models.py` aggiungendo a `Products`:
  - `brand`
  - `flyer_page`
  - `flyer_valid_from`
  - `flyer_valid_to`
  - `flyer_source`
  - `flyer_source_url`
  - `is_lidl_plus`
  - `flyer_imported_at`
  - `offer_note`
  - `discount_percent`
- aggiorna `app/services/schema_compat.py` per creare le colonne mancanti nel database online;
- aggiorna `app/routers/admin.py` per non andare più in 500 se il modello non è perfettamente allineato;
- aggiunge debug endpoint:
  - `GET /admin/debug/products-model`

## Installazione locale prima del deploy

Dalla root del progetto:

```bash
python install_admin_product_backend_fix_v16.py
```

Poi committa/pusha/deploya su Render.

## Dopo il deploy Render

Apri Swagger online e prova:

```txt
GET /admin/debug/products-model
```

Deve rispondere:

```json
{
  "has_brand": true,
  "has_flyer_valid_from": true
}
```

Se `has_brand` è ancora `false`, Render non sta usando il codice patchato.

## Se il DB online non ha ancora le colonne

Normalmente `ensure_schema_compat(engine)` le aggiunge all'avvio.

Se puoi aprire una shell su Render, puoi anche lanciare:

```bash
python scripts/migrate_schema_compat_v16.py
```

## Nota frontend

La patch v15 frontend va bene. Questo v16 è il pezzo backend che mancava.
