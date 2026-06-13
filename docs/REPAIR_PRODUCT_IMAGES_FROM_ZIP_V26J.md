# SmartGrocery v26j — Ripara immagini prodotti caricando lo ZIP

## Problema

Il bottone `Ripara immagini` ha dato:

```txt
Controllate 209, riparate 0, saltate 0
```

Questo indica che il database vede le 209 offerte/prodotti, ma il backend non trova più fisicamente i crop in:

```txt
static/images/flyer_offers/...
```

Su Render questo può succedere dopo un redeploy, perché i file creati runtime nella cartella `static/` possono non essere persistenti.

## Soluzione

Questa patch aggiunge un repair basato sullo ZIP originale del volantino.

Nuovo endpoint:

```txt
POST /admin/flyer-offer-images/repair-from-zip
```

La pagina `flyer_offers.html` mostra un nuovo box:

```txt
Ripara immagini prodotti da ZIP
```

Tu carichi lo stesso ZIP usato per importare il volantino, ad esempio:

```txt
conad_import_products_2026_06_15_27.zip
```

Il backend prende le immagini da:

```txt
product_images/*.jpg
```

e aggiorna i prodotti con:

```txt
/static/images/products/<slug>.jpg
```

## Installazione

```powershell
python install_repair_product_images_from_zip_v26j.py
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
frontend/js/flyer-offer-images-zip-repair-v26j.js
frontend/css/flyer-offer-images-zip-repair-v26j.css
```

## Uso

1. Apri `flyer_offers.html`.
2. Seleziona il volantino Conad.
3. Nel box `Ripara immagini prodotti da ZIP`, carica lo ZIP Conad.
4. Lascia attivo `forza riparazione`.
5. Clicca `Ripara da ZIP`.

## Nota

Questa patch corregge il campo `Products.image`.
Non cambia `flyer_offers.image`, che può restare collegato al crop del volantino.
