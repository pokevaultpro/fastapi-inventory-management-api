# Shopping History Analytics

Questa patch aggiunge una pagina completa per la cronologia della spesa.

## Nuovi endpoint

- `GET /shopping-history/stats`
- `GET /shopping-history/stats?days=30`
- `GET /shopping-history/recent?limit=5`
- `GET /shopping-history/{id}/items`
- `POST /shopping-history/{id}/restore-cart?clear_existing=false&merge_duplicates=true`

Gli endpoint leggono solo i dati dell'utente autenticato.

## Come funziona

Il pulsante già esistente `Finalizza Spesa` chiama:

```txt
POST /cart/finalize
```

Quello crea record in:

```txt
shopping_history
shopping_history_items
```

La nuova pagina `history.html` usa quei dati per mostrare:

- totale speso;
- numero di liste finalizzate;
- numero prodotti comprati;
- spesa media;
- risparmio stimato;
- grafico mensile;
- categorie dove spendi di più;
- supermercati dove spendi di più;
- top prodotti acquistati;
- ultime 5 liste finalizzate;
- restore intelligente di una lista.

## Restore intelligente

Quando ripristini una lista, l'app non usa i vecchi prezzi nel carrello.
Usa i prodotti attuali presenti nel catalogo.

Se un prezzo è cambiato, la risposta indica:

```txt
old_unit_price
current_unit_price
delta
```

Così il frontend mostra un messaggio tipo:

```txt
3 prezzi sono cambiati
Totale vecchio: 42,10€
Totale attuale: 45,30€
```

## File aggiunti/modificati

Backend:

```txt
app/routers/shopping_history.py
```

Frontend:

```txt
frontend/history.html
frontend/js/history.js
frontend/css/history.css
frontend/js/navbar.js
frontend/js/quick-actions.js
frontend/css/bottom-bar.css
```

## Installazione

```bash
python install_history_analytics_patch.py
```

Poi riavvia:

```bash
uvicorn app.main:app --reload
```
