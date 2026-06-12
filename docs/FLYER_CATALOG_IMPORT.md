# Flyer Catalog Import

This project now supports using supermarket flyers to populate the normal product catalog.

The app does **not** run paid OCR or AI APIs. The workflow is:

```text
flyer URL -> local screenshots -> ChatGPT vision extraction -> products.json + product_images -> API import
```

## Why products, not temporary offers?

Flyer products are imported as normal catalog products. If a product already exists for the same supermarket, the importer updates it; otherwise it creates it.

The existing `Products` table is used directly:

- `name`: product name, including brand when useful
- `category`: extracted category or `Altro`
- `original_price`: old price when available, otherwise current flyer price
- `discounted_price`: flyer price only when an old price is known and higher
- `unit`: pack size/quantity, e.g. `8 x 50 g`
- `supermarket_id`: target supermarket, created if missing
- `aisle_order`: flyer page number by default
- `image`: static product image path, e.g. `/static/images/products/gelatelli.jpg`

## Capture flyer pages

```bash
python tools/flyers/capture_flyer_images.py --url "LINK_PAGE_1" --pages 54 --fast
```

Upload `output/flyer_pages_for_chatgpt.zip` to ChatGPT.

## Expected import ZIP

The import endpoint expects:

```text
products.json
product_images/*.jpg
```

Example `products.json`:

```json
{
  "retailer": "Lidl",
  "products": [
    {
      "name": "Gelatelli biscotto gelato alla vaniglia",
      "brand": "Gelatelli",
      "category": "Gelati",
      "quantity": "8 x 50 g",
      "price": 1.29,
      "old_price": 2.59,
      "image_path": "product_images/gelatelli-biscotto-gelato.jpg",
      "page": 1
    }
  ]
}
```

Supported product fields:

- `name` or `product_name`
- `brand`
- `category`
- `quantity` or `unit`
- `price`
- `old_price`
- `original_price`
- `discounted_price`
- `image_path`, `image`, or `image_url`
- `page`
- `aisle_order`

## Import via API

```http
POST /flyer-catalog/import-zip
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

Form fields:

- `file`: the ZIP package
- `update_existing`: optional boolean, default `true`

JSON-only import is also available:

```http
POST /flyer-catalog/import-json?update_existing=true
Authorization: Bearer <token>
Content-Type: application/json
```

## Duplicate behavior

The importer checks duplicates by:

1. same supermarket
2. same product name, case-insensitive
3. same unit, when possible

If found and `update_existing=true`, it updates price/category/unit/image.

## Static images

`app/main.py` now mounts:

```text
/static -> frontend/static
```

So saved product images are reachable by the frontend.
