# SmartGrocery DB migration v9

Usa questo script quando il frontend dice cose tipo:

- "Non riesco a caricare il profilo"
- "Non riesco a salvare la ricetta"
- "Non riesco a caricare la ricetta del giorno"
- "Data del volantino non salvata"

Perché il codice nuovo è installato, ma il database vecchio non ha ancora tabelle/colonne nuove.

## Locale

Dalla root del progetto:

```bash
python scripts/migrate_profile_recipes_db.py
```

Poi riavvia:

```bash
uvicorn app.main:app --reload
```

## Online / Render

Hai due opzioni.

### Opzione A — Render Shell / console

Se puoi aprire una shell sul servizio Render, lancia:

```bash
python scripts/migrate_profile_recipes_db.py
```

### Opzione B — dal tuo PC verso il database online

Sul tuo PC devi avere la `DATABASE_URL` online.

Windows PowerShell:

```powershell
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DBNAME"
python scripts/migrate_profile_recipes_db.py
```

Windows CMD:

```cmd
set DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME
python scripts\migrate_profile_recipes_db.py
```

Mac/Linux:

```bash
export DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DBNAME"
python scripts/migrate_profile_recipes_db.py
```

## Dopo la migrazione

1. Riavvia backend.
2. Apri `/docs`.
3. Prova:
   - `GET /profile/summary`
   - `GET /smart-recipes`
   - `GET /smart-recipes/daily/today`

Se questi funzionano in Swagger, allora anche frontend profilo/ricette funzionerà.
