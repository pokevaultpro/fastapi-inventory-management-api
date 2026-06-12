# Flyer tools

## 1. Capture flyer images without OCR/API

```bash
python tools/flyers/capture_flyer_images.py --url "https://www.lidl.it/l/it/volantini/offerte-valide-dal-11-06-al-17-06-volantino-settimanale/view/flyer/page/1" --pages 54 --fast
```

This creates:

```text
output/flyer_pages_for_chatgpt.zip
```

Upload that ZIP to ChatGPT for vision extraction.

## 2. Import the catalog package produced by ChatGPT

After ChatGPT returns a package like:

```text
lidl_catalog_import.zip
  products.json
  product_images/*.jpg
```

Start the API and call:

```http
POST /flyer-catalog/import-zip
Authorization: Bearer <token>
Content-Type: multipart/form-data
file=<lidl_catalog_import.zip>
```

The importer creates or updates normal `Products` rows and copies product images to:

```text
frontend/static/images/products/
```

The product image path saved in the database is:

```text
/static/images/products/<filename>
```
