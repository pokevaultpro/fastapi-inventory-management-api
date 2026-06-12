# Install Flyer Catalog Patch

Copy these files into your project, preserving folders:

```text
app/main.py
app/routers/flyer_catalog.py
app/services/flyer_catalog_importer.py
tools/flyers/capture_flyer_images.py
tools/flyers/README.md
docs/FLYER_CATALOG_IMPORT.md
```

Then restart FastAPI.

No database migration is required because this patch imports flyer products into the existing `products` table.

The new API endpoints are:

```text
POST /flyer-catalog/import-json
POST /flyer-catalog/import-zip
```

The ZIP import expects:

```text
products.json
product_images/*.jpg
```

Images are copied to:

```text
frontend/static/images/products/
```

The app now mounts:

```text
/static -> frontend/static
```

so product images saved as `/static/images/products/<filename>` are reachable by the frontend.
