# SmartGrocery v26e — Bulk actions e immagini corrette per Offerte volantini

## Perché serviva

Nel workflow v26 le offerte avevano il crop in `flyer_offers.image`, ma quando creavi prodotti nuovi poteva finire placeholder o nessun percorso immagine corretto nel prodotto.
In più mancava la selezione multipla.

## Cosa aggiunge

Backend nuovo, senza rompere gli endpoint esistenti:

```txt
POST /admin/flyer-offers/v26e/offers/{offer_id}/create-product
POST /admin/flyer-offers/v26e/offers/{offer_id}/associate
POST /admin/flyer-offers/v26e/offers/bulk-approve
POST /admin/flyer-offers/v26e/offers/bulk-associate-suggested
POST /admin/flyer-offers/v26e/offers/bulk-create-products
POST /admin/flyer-offers/v26e/offers/bulk-reject
POST /admin/flyer-offers/v26e/repair-product-images
```

Quando crea un prodotto nuovo copia il crop da:

```txt
static/images/flyer_offers/...
```

a:

```txt
static/images/products/...
frontend/static/images/products/...
```

Il prodotto salva:

```txt
image = /static/images/products/<slug>.jpg
```

## Frontend

Aggiunge una toolbar sopra la lista offerte:

```txt
Seleziona visibili
Approva selezionate
Associa suggeriti selezionati
Crea prodotti selezionati
Scarta selezionate
Ripara immagini prodotti
```

Inoltre corregge la visualizzazione delle immagini `/static/...` usando `CONFIG.API_BASE_URL`, quindi da SiteGround vede le immagini servite da Render.

## Installazione

```powershell
python install_flyer_offers_bulk_images_fix_v26e.py
```

Poi:

```txt
commit
push
redeploy Render
```

Su SiteGround carica:

```txt
frontend/admin.html
frontend/js/flyer-offers-bulk-images-v26e.js
frontend/css/flyer-offers-bulk-images-v26e.css
```

## Cosa fare ora

1. Se hai già creato prodotti con placeholder, apri Admin → Offerte volantini e clicca `Ripara immagini prodotti`.
2. Per le offerte nuove, usa checkbox e `Crea prodotti selezionati`.
3. Per match suggeriti, usa `Associa suggeriti selezionati`.
