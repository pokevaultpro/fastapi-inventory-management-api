# SmartGrocery v26h — Offerte volantini in pagina separata

## Perché

Il widget dentro `admin.html` ha causato freeze della pagina admin.
Questa patch non tocca più `admin.html`.

Aggiunge una pagina separata:

```txt
frontend/flyer_offers.html
```

## Vantaggi

- la pagina admin principale resta sicura;
- le offerte vengono caricate 25 alla volta;
- le immagini non vengono caricate automaticamente;
- devi premere `Mostra img` per singola offerta;
- bulk actions funzionano senza renderizzare 209 card tutte insieme.

## Nuovi endpoint

```txt
GET  /admin/flyer-offers-page/flyers
GET  /admin/flyer-offers-page/flyers/{flyer_id}/offers?limit=25&offset=0
GET  /admin/flyer-offers-page/products/search
POST /admin/flyer-offers-page/offers/{offer_id}/associate
POST /admin/flyer-offers-page/offers/{offer_id}/create-product
POST /admin/flyer-offers-page/offers/{offer_id}/reject
POST /admin/flyer-offers-page/offers/bulk-approve
POST /admin/flyer-offers-page/offers/bulk-associate-suggested
POST /admin/flyer-offers-page/offers/bulk-create-products
POST /admin/flyer-offers-page/offers/bulk-reject
POST /admin/flyer-offers-page/flyers/{flyer_id}/approve-auto
POST /admin/flyer-offers-page/flyers/{flyer_id}/publish
POST /admin/flyer-offers-page/repair-product-images
```

## Installazione

```powershell
python install_flyer_offers_separate_page_v26h.py
```

Poi:

```txt
commit
push
redeploy Render
```

## SiteGround

Carica:

```txt
frontend/flyer_offers.html
frontend/js/flyer-offers-page-v26h.js
frontend/css/flyer-offers-page-v26h.css
```

Non devi rimettere il widget dentro `admin.html`.

## Uso

Apri:

```txt
https://TUO-SITO/flyer_offers.html
```

Poi:

1. selezioni il volantino;
2. lavori 25 offerte alla volta;
3. usi i filtri;
4. usi le checkbox per bulk actions;
5. pubblichi solo le approvate.

## Nota immagini

Le immagini non vengono caricate automaticamente per evitare freeze.
Ogni riga ha il bottone:

```txt
Mostra img
```

Quando crei un prodotto, se il crop esiste ancora su backend, viene copiato in:

```txt
/static/images/products/...
frontend/static/images/products/...
```
