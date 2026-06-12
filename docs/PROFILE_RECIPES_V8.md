# SmartGrocery — Profilo + Ricette v8

Questa patch corregge la v7 e rende la sezione ricette più stabile.

## Fix principali

- Profilo più robusto: gli endpoint controllano/aggiornano automaticamente le colonne mancanti del database.
- Salvataggio ricette più robusto: le colonne extra di `recipes` e `recipe_items` vengono create se mancanti.
- Ricetta del giorno senza siti esterni: niente TheMealDB o siti americani. La ricetta del giorno è una rotazione locale di ricette italiane semplici.
- Frontend ricette/profilo non dipende più dalla funzione globale `apiFetch`, quindi funziona meglio con script `type="module"`.
- Messaggi errore più chiari in caso di backend non raggiungibile o token scaduto.

## Dopo installazione

Riavvia FastAPI e fai hard refresh del browser.

```bash
uvicorn app.main:app --reload
```

Poi apri:

- `profile.html`
- `recipes.html`

## Ricetta del giorno

La ricetta del giorno ora è locale e italiana. Gli ingredienti vengono abbinati al tuo catalogo prodotti e la ricetta mostra il prezzo totale stimato in base ai prodotti trovati.
