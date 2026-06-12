# SmartGrocery v12 — Role badge in profile

Aggiunge nel profilo una card "Ruolo account":

- Admin → badge verde "Admin"
- User → badge blu "Utente"

Aggiunge anche endpoint:

```txt
GET /profile/role
```

Questo legge il ruolo dal database, così capisci se l'utente è admin anche se il frontend non lo mostrava.

## Installazione

Dalla root del progetto:

```bash
python install_profile_role_v12.py
uvicorn app.main:app --reload
```

Poi fai hard refresh su `profile.html`.

## Importante

Se hai cambiato ruolo nel DB da poco, fai logout/login perché il token vecchio può contenere ancora il ruolo precedente.
