# SmartGrocery History Analytics Patch v1

Installa una pagina cronologia/statistiche per la spesa.

## Installazione

Estrai questo ZIP nella root del progetto e lancia:

```bash
python install_history_analytics_patch.py
```

Poi riavvia FastAPI:

```bash
uvicorn app.main:app --reload
```

Apri:

```txt
frontend/history.html
```

Oppure, se sei online:

```txt
https://tuodominio.it/history.html
```

## Cosa aggiunge

- dashboard statistiche personale;
- grafico spesa mensile;
- grafico supermercati;
- spesa per categoria;
- top prodotti acquistati;
- ultime 5 liste finalizzate;
- restore di una lista nel carrello;
- segnalazione prezzi cambiati durante il restore.
