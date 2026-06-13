# SmartGrocery v22 — Admin storico spese + restyling negozi

## 1. Admin: modifica cronologia spesa utenti

Aggiunge una nuova sezione nella pagina `admin.html`:

```txt
Storico spese
```

Da lì puoi:

- selezionare un utente;
- vedere tutte le sue spese passate;
- aprire una spesa;
- modificare prodotti già acquistati;
- modificare quantità, prezzo unitario, totale finale, categoria, supermercato, tipo prezzo e peso;
- aggiungere prodotti manuali o da catalogo a una spesa passata;
- eliminare prodotti da una spesa passata;
- eliminare una lista storica;
- ricalcolare i totali.

## 2. Nuovi endpoint backend

```txt
GET    /admin/history/debug
GET    /admin/history/users
GET    /admin/history/user/{user_id}
GET    /admin/history/{history_id}
PUT    /admin/history/{history_id}
DELETE /admin/history/{history_id}
GET    /admin/history/{history_id}/items
POST   /admin/history/{history_id}/items
PUT    /admin/history/items/{item_id}
DELETE /admin/history/items/{item_id}
POST   /admin/history/{history_id}/recalculate
```

## 3. Pagina negozi migliorata

Ridisegna `supermarkets.html` desktop e mobile:

- hero moderna;
- ricerca negozio;
- ordinamento negozi per nome, offerte o prodotti;
- card negozi più belle;
- dettaglio negozio con statistiche;
- ricerca prodotti dentro il negozio;
- ordinamento per corsia, offerte, nome o prezzo;
- card prodotto più belle;
- supporto badge offerta, al peso, manuale;
- layout mobile molto più leggibile.

## Installazione

Dalla root del progetto:

```powershell
python install_admin_history_stores_v22.py
```

Poi fai commit/push/deploy su Render.

## File frontend da caricare su SiteGround

```txt
frontend/admin.html
frontend/css/admin.css
frontend/js/admin-history.js
frontend/supermarkets.html
frontend/css/supermarkets.css
frontend/js/supermarkets.js
```

Poi fai:

```txt
Ctrl + F5
```

## Controlli dopo deploy

In Swagger online:

```txt
GET /admin/history/debug
GET /admin/history/users
```

Devono rispondere senza errori se sei loggato come admin.
