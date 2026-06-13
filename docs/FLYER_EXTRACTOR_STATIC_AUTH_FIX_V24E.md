# SmartGrocery v24e — Fix immagini/ZIP Flyer Extractor

## Problemi risolti

Dopo l'estrazione PDF:

```txt
Scarica ZIP pagine -> {"detail":"Not authenticated"}
Contact sheet / pagine singole -> {"detail":"Not Found"}
```

## Perché succedeva

### ZIP

Il download ZIP era un link normale `<a href="...">`.

I link normali del browser NON mandano il token JWT, quindi l'endpoint protetto rispondeva:

```json
{"detail":"Not authenticated"}
```

### Immagini

Le immagini erano salvate in:

```txt
static/flyer_pages/...
```

ma FastAPI non montava `/static`, quindi il browser riceveva:

```json
{"detail":"Not Found"}
```

## Cosa fa la patch

- `frontend/admin.html` scarica lo ZIP con `fetch()` autenticato e poi crea un download Blob.
- Il manifest viene scaricato/copiato direttamente dal browser, senza richiamare endpoint protetti.
- `app/main.py` monta:

```python
app.mount('/static', StaticFiles(directory='static'), name='static')
```

così contact sheet e pagine singole diventano visibili.

## Installazione

Dalla root:

```powershell
python install_flyer_extractor_static_auth_fix_v24e.py
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
```

Poi:

```txt
Ctrl + F5
```

## Nota

Le estrazioni già fatte prima possono funzionare dopo il redeploy, finché i file esistono ancora nel filesystem Render.
Se Render si è riavviato e i file sono spariti, rifai l'estrazione PDF.
