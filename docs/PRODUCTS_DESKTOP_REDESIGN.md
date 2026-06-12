# Products desktop redesign + flyer metadata

Questa patch rivoluziona la pagina `products.html`, soprattutto da desktop.

## Cosa cambia nel frontend

- Layout desktop a due colonne: filtri a sinistra, griglia prodotti a destra.
- Card prodotto responsive, senza virtual scroll desktop.
- Griglia multi-colonna: da computer si vedono molti prodotti alla volta.
- Hero con statistiche: totale prodotti, prodotti in sconto, supermercati.
- Filtri rapidi: Tutti, Solo offerte, Lidl Plus, Preferiti.
- Categorie generate dinamicamente dal catalogo.
- Ordinamenti: miglior sconto, pagina volantino, prezzo, nome, categoria.
- Badge su card:
  - percentuale sconto;
  - pagina del volantino;
  - Lidl Plus;
  - validità offerta.
- Modal prodotto aggiornata con pagina volantino e date validità.

## Cosa cambia nel backend

La tabella `products` riceve campi opzionali per i dati del volantino:

- `brand`
- `flyer_page`
- `flyer_valid_from`
- `flyer_valid_to`
- `flyer_source`
- `flyer_source_url`
- `is_lidl_plus`
- `flyer_imported_at`
- `offer_note`
- `discount_percent`

Questi campi sono nullable e non rompono i prodotti esistenti.

## Migrazione automatica leggera

La patch aggiunge `app/services/schema_compat.py` e fa chiamare:

```python
ensure_product_metadata_columns(engine)
```

all'avvio dell'app. Serve perché `Base.metadata.create_all()` non aggiunge colonne a una tabella già esistente.

## Import volantini

L'importer `flyer_catalog_importer.py` ora salva anche:

- pagina volantino;
- validità offerta;
- Lidl Plus;
- percentuale sconto;
- note.

Quindi, dopo aver reimportato lo ZIP Lidl, la UI potrà mostrare `Volantino p.X` sulle card.

## Dopo installazione

1. Riavvia FastAPI.
2. Apri `/docs` e reimporta lo ZIP catalogo Lidl con `update_existing=true`.
3. Apri `products.html` e fai hard refresh.

Se avevi già importato i prodotti prima della patch, reimporta lo stesso ZIP: i prodotti verranno aggiornati con pagina volantino e metadati offerta.
