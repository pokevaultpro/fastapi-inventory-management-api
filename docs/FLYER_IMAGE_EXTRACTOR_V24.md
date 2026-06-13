# SmartGrocery v24 — Flyer Image Extractor

## Obiettivo

Aggiunge una sezione admin:

```txt
Volantini → Flyer Image Extractor
```

Questa feature NON fa OCR e NON prova a leggere i prodotti.

Fa solo:

```txt
PDF volantino → immagini pagina
ZIP immagini → pagine importate
URL diretto PDF/immagine → pagine importate
```

Poi le immagini pagina possono essere lette manualmente o inviate a ChatGPT per preparare un JSON/CSV pulito delle offerte.

## Perché niente OCR

L'OCR sbaglia spesso prezzi e unità, soprattutto:

```txt
1,59 €/kg
0,85 €/etto
SOLO TITOLARI
a partire da
-20%
validità speciali
```

Quindi l'app deve solo generare le immagini. L'estrazione prodotti rimane manuale/assistita da ChatGPT.

## Endpoint backend

```txt
GET    /admin/flyer-extractor/health
GET    /admin/flyer-extractor/recent
POST   /admin/flyer-extractor/pdf
POST   /admin/flyer-extractor/images-zip
POST   /admin/flyer-extractor/url
GET    /admin/flyer-extractor/{extraction_id}/manifest
GET    /admin/flyer-extractor/{extraction_id}/zip
DELETE /admin/flyer-extractor/{extraction_id}
```

## Input supportati

### 1. PDF

Carichi un PDF e il backend crea:

```txt
static/flyer_pages/<id>/page_001.jpg
static/flyer_pages/<id>/page_002.jpg
...
manifest.json
contact_sheet.jpg
pages.zip
```

### 2. ZIP immagini

Per siti senza PDF, come spesso Lidl:

```txt
ChatGPT / script esterno genera immagini pagina
tu carichi lo ZIP
l'app lo organizza come volantino
```

### 3. URL diretto

Funziona solo se l'URL è direttamente:

```txt
https://.../volantino.pdf
https://.../page_001.jpg
```

Non analizza siti HTML.

## Installazione

Dalla root del progetto:

```powershell
python install_flyer_image_extractor_v24.py
```

Poi:

```txt
commit
push
redeploy Render
```

L'installer aggiunge anche a `requirements.txt`:

```txt
PyMuPDF>=1.24.0
Pillow>=10.0.0
```

## Frontend SiteGround

Carica:

```txt
frontend/admin.html
frontend/js/flyer-extractor-admin.js
frontend/css/flyer-extractor-admin.css
```

Poi fai:

```txt
Ctrl + F5
```

## Controllo

In Swagger online:

```txt
GET /admin/flyer-extractor/health
```

Deve rispondere:

```json
{
  "ok": true,
  "no_ocr": true,
  "pymupdf_available": true,
  "pillow_available": true
}
```

## Uso pratico

### Caso Conad con PDF

```txt
Admin → Volantini
Titolo: Conad Super Risparmio
Validità: 2026-06-15 → 2026-06-27
Carica PDF
Scarica ZIP pagine o apri pagine singole
```

### Caso Lidl senza PDF

```txt
Tu mi mandi il link/screenshot/sito
io ti preparo ZIP immagini pagina
tu carichi ZIP nella sezione Volantini
```

## Script locale opzionale

Se vuoi estrarre pagine PDF senza usare Render:

```powershell
python scripts\flyer_image_extractor_local_v24.py "C:\path\volantino.pdf" --out conad_pages
```

Crea:

```txt
conad_pages/page_001.jpg
conad_pages/page_002.jpg
...
conad_pages/<nome>_pages.zip
```
