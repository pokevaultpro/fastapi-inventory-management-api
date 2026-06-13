# SmartGrocery v24c — Flyer Image Extractor dentro Admin

## Problema

La v24b aveva creato una pagina autonoma:

```txt
flyer-extractor.html
```

ma la scelta corretta è tenere tutto dentro `admin.html`.

## Cosa fa v24c

- mette il Flyer Image Extractor dentro la pagina admin;
- aggiunge tab/bottone `Volantini`;
- non usa più `flyer-extractor.html`;
- rimuove localmente i file standalone creati dalla v24b, se presenti;
- lascia invariato il backend già funzionante `/admin/flyer-extractor/...`.

## Installazione

Dalla root:

```powershell
python install_flyer_extractor_admin_v24c.py
```

## File SiteGround da caricare

```txt
frontend/admin.html
frontend/js/flyer-extractor-admin-v24c.js
frontend/css/flyer-extractor-admin-v24c.css
```

Poi fai:

```txt
Ctrl + F5
```

## Se avevi già caricato v24b su SiteGround

Puoi eliminare da SiteGround questi file vecchi:

```txt
flyer-extractor.html
js/flyer-extractor-page.js
js/flyer-extractor-admin-link.js
css/flyer-extractor-page.css
```

Non sono più necessari.

## Controllo backend

Il backend è già ok se Swagger restituisce:

```json
{
  "ok": true,
  "no_ocr": true,
  "pymupdf_available": true,
  "pillow_available": true
}
```

## Uso

Vai in:

```txt
admin.html
```

e apri:

```txt
Volantini
```

Da lì puoi caricare PDF/ZIP immagini, vedere contact sheet, scaricare ZIP pagine.
