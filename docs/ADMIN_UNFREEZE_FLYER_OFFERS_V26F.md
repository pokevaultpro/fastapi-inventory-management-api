# SmartGrocery v26f — Hotfix admin page bloccata

## Problema

La pagina admin poteva bloccarsi nella sezione `Offerte volantini`.

Cause probabili:

1. molte immagini offerta non più presenti su Render dopo redeploy;
2. `/static/...` o placeholder immagine non raggiungibile;
3. caricamento simultaneo di centinaia di crop;
4. troppi listener e troppe card renderizzate tutte insieme.

## Fix

Questa patch frontend:

- usa un placeholder SVG inline, quindi niente loop di `onerror`;
- carica le immagini in `lazy`;
- mostra solo 40 offerte alla volta;
- aggiunge `Mostra altre 40`;
- usa event delegation invece di mille listener;
- non fa rendering pesante all'apertura della pagina.

## Installazione

```powershell
python install_admin_unfreeze_flyer_offers_v26f.py
```

## SiteGround

Carica:

```txt
frontend/js/flyer-offers-admin-v26.js
frontend/css/flyer-offers-admin-v26.css
```

Poi:

```txt
Ctrl + F5
```

Oppure apri admin in finestra anonima.
