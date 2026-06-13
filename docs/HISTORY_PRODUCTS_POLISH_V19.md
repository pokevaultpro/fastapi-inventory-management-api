# SmartGrocery v19 — Volantino corretto, aisle order, admin role, storico prodotti

## Cosa corregge

### Prodotti / Volantino

I prodotti non scontati non mostrano più:

- pagina del volantino
- validità volantino
- Lidl Plus come contesto offerta

La pagina del volantino compare solo se il prodotto ha una vera offerta attiva:

```txt
discounted_price > 0
discounted_price < original_price
offerta non scaduta
```

### Aisle order

`aisle_order` e `flyer_page` sono separati.

- `aisle_order` = ordine interno nel supermercato/corsia;
- `flyer_page` = pagina del volantino, solo per controllare un'offerta.

La lista della spesa usa `aisle_order` solo quando filtri un supermercato specifico.

### Admin page

La pagina `admin.html` mostra il ruolo corrente:

```txt
Ruolo corrente: Admin / Utente
DB role
Token role
```

Così capisci subito se stai entrando come admin.

### Storico

Aggiunge:

```txt
GET /shopping-history/products
```

e nella pagina storico una sezione:

```txt
Tutti i prodotti comprati
```

Con:

- prodotti unici acquistati;
- prodotto più comprato;
- categoria preferita;
- percentuale di acquisti scontati;
- supermercato principale;
- anteprima dei prodotti più comprati;
- pulsante "Vedi tutti" con archivio completo e ricerca.

## Installazione

Dalla root del progetto:

```powershell
python install_history_products_polish_v19.py
```

Poi fai deploy backend su Render e carica il frontend su SiteGround.

## File frontend da caricare su SiteGround

```txt
frontend/products.html non serve
frontend/js/products.js
frontend/js/modal-function.js
frontend/js/shopping.js
frontend/history.html
frontend/js/history.js
frontend/js/history-all.js
frontend/js/history-products.js
frontend/css/history.css
frontend/admin.html
frontend/js/admin-role.js
frontend/css/admin.css
```

Poi fai hard refresh:

```txt
Ctrl + F5
```

## Controlli backend

In Swagger online controlla:

```txt
GET /shopping-history/products
```

Deve rispondere con `overview` e `products`.

## Nota

Questa patch non cambia il database. Usa campi già esistenti:
`aisle_order`, `flyer_page`, `discounted_price`, `original_price`, `flyer_valid_to`.
