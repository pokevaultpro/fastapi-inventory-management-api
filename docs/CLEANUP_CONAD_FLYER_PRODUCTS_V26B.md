# SmartGrocery v26b — Cleanup prodotti Conad importati per errore nel catalogo

## Obiettivo

Rimuovere dal database i prodotti Conad importati direttamente dentro `Products` dal volantino 15–27 giugno 2026.

Questa pulizia serve prima di usare il nuovo workflow v26:

```txt
volantino -> flyer_offers draft
```

invece di:

```txt
volantino -> products diretto
```

## Criterio di selezione

Lo script cancella solo prodotti che rispettano entrambe le condizioni:

```txt
supermercato con nome contenente "Conad"
```

e almeno una tra:

```txt
flyer_page IS NOT NULL
flyer_valid_from = 2026-06-15
flyer_valid_to = 2026-06-27
flyer_source contiene "conad"
```

Quindi non dovrebbe toccare prodotti Conad normali già presenti prima, se non hanno campi volantino.

## Sicurezza

Di default lo script fa solo dry-run:

```powershell
python scripts\cleanup_conad_flyer_products_v26b.py
```

Il dry-run crea un report CSV in:

```txt
cleanup_reports/
```

e mostra:

```txt
prodotti candidati
prime righe
righe collegate da cart/favorites/history/recipe_items ecc.
```

## Cancellazione reale

Solo dopo aver controllato il conteggio:

```powershell
python scripts\cleanup_conad_flyer_products_v26b.py --execute
```

Per cancellare anche i file immagine locali collegati:

```powershell
python scripts\cleanup_conad_flyer_products_v26b.py --execute --delete-images
```

## Render

Su Render Shell:

```bash
python scripts/cleanup_conad_flyer_products_v26b.py
```

Poi:

```bash
python scripts/cleanup_conad_flyer_products_v26b.py --execute
```

## Nota dependencies

Se quei prodotti sono finiti in carrello, preferiti, storico spesa o ricette, lo script cancella prima le righe collegate e poi i prodotti, evitando errori di foreign key.

Questo è voluto perché questi prodotti sono stati importati per errore.
