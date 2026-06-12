# SmartGrocery v11 — Admin, ricette edit/delete, storico completo

## Cosa risolve

- Aggiunta ingrediente in ricetta: ora NON salva più la ricetta automaticamente.
  Il bug era causato dai bottoni ingredienti dentro un `<form>` senza `type="button"`.
- Ricette personali: puoi modificare ed eliminare.
- Storico spesa: resta visibile il blocco "Ultime 5 liste", ma ora c'è anche "Vedi tutte".
  Da lì puoi aprire e ripristinare qualsiasi lista finalizzata.
- Admin page desktop: `admin.html`, solo per utenti con role `admin`.

## Installazione

Dalla root del progetto:

```bash
python install_admin_recipes_history_v11.py
python scripts/migrate_profile_recipes_db.py
uvicorn app.main:app --reload
```

Poi hard refresh del browser.

## Admin

Endpoint backend:

- `GET /admin/summary`
- `GET/POST/PUT/DELETE /admin/products`
- `GET/POST/PUT/DELETE /admin/supermarkets`
- `GET/PUT /admin/users`
- `GET/POST/PUT/DELETE /admin/recipes`

La pagina `admin.html` è pensata solo desktop. Da telefono mostra un messaggio e non carica la dashboard admin.

## Importante: ruolo admin

La pagina admin funziona solo se nel token hai:

```json
{"role": "admin"}
```

Se il tuo utente è ancora role `user`, devi cambiarlo nel database oppure usare un utente già admin.
