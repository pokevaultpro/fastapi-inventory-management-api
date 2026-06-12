# SmartGrocery Polish v6

Patch grafica e funzionale.

## Modifiche principali

- Pagina storico migliorata su mobile e desktop.
- Bottom bar mobile con icona Storico sempre presente.
- Grafico spesa nel tempo rifatto: barre + linea, punti visibili, tooltip hover/click/touch.
- Grafico distribuzione supermercati stabilizzato: non si sposta più quando cambi range.
- Home page ridisegnata per desktop e mobile, mantenendo la sezione Ricette.
- Cuore preferiti reso chiaramente cliccabile.
- Validità volantino: se il prodotto viene da un volantino con date generali, quelle date valgono per tutti i prodotti se non diversamente indicato.
- Dopo la data di fine volantino, lo sconto viene considerato scaduto automaticamente lato UI e nei calcoli principali backend inclusi finalizzazione carrello e restore storico.

## Installazione

Estrai nella root del progetto e lancia:

```bash
python install_smartgrocery_polish_v6.py
```

Poi riavvia FastAPI e fai hard refresh del browser.

```bash
uvicorn app.main:app --reload
```

## Nota validità volantini

Per vedere le date corrette su prodotti già importati prima della patch, reimporta lo ZIP catalogo con:

```txt
POST /flyer-catalog/import-zip
update_existing = true
```

Lo ZIP completo Lidl `lidl_catalog_import_pages_001_054.zip` contiene già `valid_from` e `valid_to` a livello volantino.
