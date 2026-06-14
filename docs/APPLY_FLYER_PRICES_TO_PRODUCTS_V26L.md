# SmartGrocery v26l — Applica prezzi FlyerOffers dentro Products

## Problema

Il workflow corretto salva le offerte in `flyer_offers`.

Però il frontend storico del progetto riconosce le offerte guardando ancora:

```txt
Products.original_price
Products.discounted_price
```

Quindi, se una offerta viene salvata solo in `flyer_offers`, il prodotto può non apparire come "in offerta" nella pagina prodotti/lista spesa.

## Soluzione

Questa patch aggiunge un layer di compatibilità.

Quando hai approvato/associato le offerte di un volantino, puoi cliccare:

```txt
Pubblica + applica prezzi
```

La patch copia nei prodotti:

```txt
Products.discounted_price = flyer_offers.offer_price
Products.original_price   = flyer_offers.original_price se presente,
                            altrimenti il prezzo normale del prodotto se maggiore dell'offerta
Products.flyer_valid_from = flyer_offers.valid_from
Products.flyer_valid_to   = flyer_offers.valid_to
Products.flyer_page       = flyer_offers.flyer_page
```

La source of truth resta `flyer_offers`, ma i campi `Products` vengono materializzati per far funzionare il frontend esistente.

## Nuovi endpoint

```txt
POST /admin/flyer-offer-prices/apply/{flyer_id}
POST /admin/flyer-offer-prices/publish-and-apply/{flyer_id}
POST /admin/flyer-offer-prices/clear-expired
```

## Installazione

```powershell
python install_apply_flyer_prices_to_products_v26l.py
```

Poi:

```txt
commit
push
redeploy Render
```

## SiteGround

Caricare:

```txt
frontend/flyer_offers.html
frontend/js/flyer-offer-apply-prices-v26l.js
frontend/css/flyer-offer-apply-prices-v26l.css
```

## Uso

1. Importa lo ZIP finale del volantino.
2. Vai su `flyer_offers.html`.
3. Associa/crea/approva le offerte.
4. Clicca `Pubblica + applica prezzi`.
5. I prodotti collegati avranno `discounted_price` uguale al prezzo volantino e `original_price` uguale al prezzo barrato/catalogo quando disponibile.

## Nota

Se `flyer_offers.original_price` è mancante e il prodotto non ha già un prezzo normale maggiore dell'offerta, il prodotto viene aggiornato col prezzo offerta ma potrebbe non mostrare il barrato. Per questo gli ZIP creati da ChatGPT devono cercare di compilare `original_price` dal prezzo barrato del volantino.
