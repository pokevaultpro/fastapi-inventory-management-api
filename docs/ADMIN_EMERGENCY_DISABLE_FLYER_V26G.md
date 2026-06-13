# SmartGrocery v26g — Emergency disable Offerte volantini

## Problema

La pagina `admin.html` si blocca completamente e il browser chiede di uscire dalla pagina.

## Soluzione rapida

Questa patch sostituisce:

```txt
frontend/js/flyer-offers-admin-v26.js
frontend/css/flyer-offers-admin-v26.css
```

con versioni vuote/sicure.

Il file `admin.html` può anche continuare a importarli, ma non eseguono più nulla.

## Installazione

```powershell
python install_admin_emergency_disable_flyer_v26g.py
```

## SiteGround

Carica:

```txt
frontend/js/flyer-offers-admin-v26.js
frontend/css/flyer-offers-admin-v26.css
```

Poi apri admin in finestra anonima o fai Ctrl+F5.

## Dopo

La admin deve tornare normale.
Il workflow volantini va spostato in una pagina separata, non più dentro admin.html.
