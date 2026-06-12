# Flyer patch installer v4

Questa versione aggiunge due cose:

1. Endpoint:
   - `POST /flyer-catalog/import-zip`
   - `POST /flyer-catalog/import-json`

2. Quando importi uno ZIP catalogo, le immagini vengono copiate in due posti:
   - `frontend/static/images/products/` per il frontend
   - `imported_flyer_images/<import_name>/product_images/` come cartella separata consultabile sul computer

## Installazione

Estrai questo ZIP nella root del progetto, poi:

```bash
python install_flyer_patch.py
```

Poi riavvia:

```bash
uvicorn app.main:app --reload
```

Apri:

```txt
http://127.0.0.1:8000/docs
```

## Import

Usa:

```txt
POST /flyer-catalog/import-zip
```

Parametri:
- `file`: ZIP catalogo, ad esempio `lidl_catalog_import_pages_001_011_v2.zip`
- `update_existing`: true
- `save_archive_folder`: true

Dopo l'import vedrai nella risposta:

```txt
image_archive_folder
image_archive_product_images_folder
```

E sul computer troverai la cartella:

```txt
imported_flyer_images/<import_name>/product_images/
```
