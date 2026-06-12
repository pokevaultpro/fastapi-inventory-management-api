# SmartGrocery v15 — Admin product creation improvements

## Cosa cambia

Nella pagina `admin.html`, sezione Prodotti:

- mostra errori reali quando il prodotto non viene salvato;
- valida lato frontend i campi obbligatori;
- aggiunge `aisle_order`;
- aggiunge `location`, cioè posizione nel supermercato, esempio:
  - `Reparto Pane e prodotti da forno`
  - `Corsia 3`
  - `Banco frigo`
- aggiunge valori nutrizionali:
  - calorie
  - grassi
  - carboidrati
  - proteine
- aggiunge validità volantino manuale:
  - `flyer_valid_from`
  - `flyer_valid_to`
- aggiunge flag Lidl Plus e nota offerta.

## Campi obbligatori per creare un prodotto

- Nome prodotto
- Categoria
- Prezzo originale maggiore di 0
- Supermercato

Se manca qualcosa, ora la pagina lo dice chiaramente invece di mostrare solo un errore generico.

## Installazione

Dalla root del progetto:

```bash
python install_admin_product_fields_v15.py
```

Poi riavvia/deploya e fai hard refresh su `admin.html`.

## Online

Se lavori sul sito online:

- backend Render: serve solo se non hai ancora la pagina admin/API admin aggiornata;
- frontend SiteGround: devi caricare questi file aggiornati:
  - `admin.html`
  - `js/admin.js`
  - `css/admin.css`
