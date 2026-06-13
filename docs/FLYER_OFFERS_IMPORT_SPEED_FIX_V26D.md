# SmartGrocery v26d — Fix import ZIP volantini bloccato/lento

## Problema

Con ZIP grandi, ad esempio Conad con 209 prodotti e 209 crop, l'import in `Offerte volantini` poteva sembrare bloccato.

La causa principale era il matching:

```txt
per ogni prodotto del volantino
  ricarica tutto il catalogo prodotti dal database
```

Con 200+ prodotti questo può diventare molto lento su Render.

## Fix

`app/services/flyer_offer_importer.py` ora:

```txt
carica i prodotti candidati una sola volta
carica gli alias una sola volta
riusa questi dati per tutte le righe del volantino
fa un solo commit finale
ritorna elapsed_seconds
```

Il frontend mostra anche:

```txt
Import in corso...
Completato in X secondi
```

## Installazione

```powershell
python install_flyer_offers_import_speed_fix_v26d.py
```

Poi:

```txt
commit
push
redeploy Render
```

Su SiteGround caricare:

```txt
frontend/js/flyer-offers-admin-v26.js
frontend/css/flyer-offers-admin-v26.css
```

## Nota

Lo ZIP Conad `conad_import_products_2026_06_15_27.zip` è corretto.
Contiene:

```txt
products.json
209 immagini in product_images/
209 prodotti
```

Quindi non serve rifarlo.
