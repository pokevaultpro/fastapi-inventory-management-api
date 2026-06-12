# SmartGrocery v14 — Rendere admin l'utente sul sito online

Il locale non modifica il sito online. Per rendere admin l'utente `mike` sul sito, devi modificare il database online.

Questa patch aggiunge un endpoint sicuro:

```txt
POST /admin-bootstrap/promote-me
```

Promuove ad admin l'utente attualmente loggato, ma solo se conosce il secret `ADMIN_BOOTSTRAP_TOKEN`.

## Flusso online

### 1. Installa/deploya questa patch sul backend online

Dopo installazione locale e push/deploy su Render, in Swagger devono comparire:

```txt
GET /admin-bootstrap/status
POST /admin-bootstrap/promote-me
GET /profile/role
```

### 2. Imposta la variabile Render

Nel servizio backend Render aggiungi una environment variable:

```txt
ADMIN_BOOTSTRAP_TOKEN=una_password_lunga_a_caso
```

Esempio:

```txt
ADMIN_BOOTSTRAP_TOKEN=sg_bootstrap_2026_cambia_subito
```

Poi riavvia/redeploya il backend.

### 3. Login come mike sul sito

Entra normalmente nel sito con l'utente `mike`.

### 4. Vai nello Swagger online

Apri:

```txt
https://TUO-BACKEND-RENDER.onrender.com/docs
```

Premi **Authorize** e incolla il token JWT.

Se non hai il token a mano, puoi fare login dall'app e leggerlo dal localStorage del browser.

### 5. Chiama promote-me

Esegui:

```txt
POST /admin-bootstrap/promote-me
```

Body:

```json
{
  "setup_token": "la_stessa_password_che_hai_messo_su_Render"
}
```

Risposta attesa:

```json
{
  "ok": true,
  "old_role": "user",
  "new_role": "admin"
}
```

### 6. Logout/login

Fai logout/login sul sito. Poi `/profile/role` deve dare:

```json
{
  "role": "admin",
  "db_role": "admin",
  "is_admin": true
}
```

## Dopo averlo fatto

Puoi anche eliminare o cambiare `ADMIN_BOOTSTRAP_TOKEN`, così nessuno può usare il bootstrap.
