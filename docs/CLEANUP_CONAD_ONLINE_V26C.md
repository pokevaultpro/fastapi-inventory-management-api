# SmartGrocery v26c — Cleanup Conad online, senza Render Shell

## Problema

Non puoi usare Render Shell, quindi lo script `cleanup_conad_flyer_products_v26b.py` non è comodo.

## Soluzione

Questa patch aggiunge endpoint admin protetti e una sezione nella pagina admin.

## Endpoint

```txt
GET  /admin/cleanup/conad-flyer-products/preview
POST /admin/cleanup/conad-flyer-products/execute
```

Sono endpoint admin-only.

## Cosa cancella

Solo prodotti:

```txt
supermarket.name contiene Conad
```

e con almeno uno di questi segnali:

```txt
flyer_page IS NOT NULL
flyer_valid_from = 2026-06-15
flyer_valid_to = 2026-06-27
flyer_source contiene conad
```

## Uso da admin page

1. Apri Admin.
2. Vai nella zona `Offerte volantini` o `Flyer Image Extractor`.
3. Trovi il box rosso `Rimuovi prodotti Conad importati per errore`.
4. Clicca `Anteprima`.
5. Se il conteggio è corretto, clicca `Cancella candidati`.

## Installazione

Dalla root locale:

```powershell
python install_cleanup_conad_online_v26c.py
```

Poi:

```txt
commit
push
redeploy Render
```

## SiteGround

Carica:

```txt
frontend/admin.html
frontend/js/conad-cleanup-admin-v26c.js
frontend/css/conad-cleanup-admin-v26c.css
```

## Nota

Per sicurezza, il backend richiede `confirm=true` sul POST di cancellazione.
Dal frontend viene mandato automaticamente solo quando clicchi `Cancella candidati`.
