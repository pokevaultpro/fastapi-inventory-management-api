# SmartGrocery v26i — Fix percorso immagini prodotto

## Problema

Le offerte hanno correttamente immagini crop in:

```txt
/static/images/flyer_offers/...
```

Ma `Products.image` deve usare:

```txt
/static/images/products/...
```

Non deve salvare:

```txt
https://pokevault-backend.onrender.com/static/images/flyer_offers/...
```

né:

```txt
/static/images/flyer_offers/...
```

## Differenza corretta

```txt
flyer_offers.image = /static/images/flyer_offers/...
products.image     = /static/images/products/...
```

Il frontend può trasformare `/static/...` in URL completo solo per visualizzare, ma nel database dei prodotti deve restare il path relativo `/static/images/products/...`.

## Cosa cambia

Quando crei un prodotto da offerta:

1. prende il crop da `flyer_offers.image`;
2. lo copia in `static/images/products/`;
3. prova a copiarlo anche in `frontend/static/images/products/`;
4. salva nel prodotto:

```txt
/static/images/products/<slug>.jpg
```

## Repair

Il bottone `Ripara immagini` ora corregge prodotti collegati alle offerte che hanno:

```txt
placeholder
URL assoluto
/static/images/flyer_offers/...
qualsiasi path che non inizi con /static/images/products/
```

## Installazione

```powershell
python install_product_image_path_fix_v26i.py
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
frontend/js/flyer-offers-page-v26h.js
frontend/css/flyer-offers-page-v26h.css
```

## Uso

Apri:

```txt
flyer_offers.html
```

Se hai già creato prodotti con percorso sbagliato, clicca:

```txt
Ripara immagini
```

Poi controlla le righe: ora vedrai badge:

```txt
img prodotto: PRODUCT
```

quando il path è corretto.
