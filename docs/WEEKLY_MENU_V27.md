# SmartGrocery v27 — Menu Settimanale

## Cosa aggiunge

Nuova sezione:

```txt
weekly-menu.html
```

Funzioni:

- planner settimanale con 7 giorni
- slot: Colazione, Pranzo, Spuntino, Cena
- selezione ricette già presenti nel tuo account
- costo stimato della settimana
- duplicazione della settimana successiva
- aggiunta ingredienti del menu alla lista della spesa
- download PDF con layout bello e immagini ricette

## Backend

Nuovo router:

```txt
app/routers/weekly_menus.py
```

Endpoint:

```txt
GET    /weekly-menus?week_start=YYYY-MM-DD
GET    /weekly-menus/recipes
POST   /weekly-menus/item
DELETE /weekly-menus/item/{item_id}
POST   /weekly-menus/{menu_id}/add-to-cart
POST   /weekly-menus/{menu_id}/duplicate-next-week
```

## Tabelle create

```txt
weekly_menus
weekly_menu_items
```

Il router crea le tabelle automaticamente al primo utilizzo.  
Puoi anche lanciare:

```powershell
python scripts\migrate_weekly_menu_v27.py
```

## Installazione

Dalla root progetto:

```powershell
python install_weekly_menu_v27.py
```

Poi:

```powershell
git add .
git commit -m "Add weekly menu planner"
git push
```

Redeploy su Render.

## SiteGround

Carica:

```txt
frontend/weekly-menu.html
frontend/js/weekly-menu.js
frontend/css/weekly-menu.css
```

Se vuoi la route dal menu, carica anche:

```txt
frontend/js/navbar.js
```

Apri:

```txt
https://TUO-SITO/weekly-menu.html
```

## PDF

Il PDF viene generato lato frontend con jsPDF via CDN e prova a includere le immagini delle ricette/prodotti.


## v27c PDF polish

Migliorie:

- PDF più pulito e moderno
- header verde con riepilogo pasti/costo
- card settimanali più leggibili
- pagina dettaglio ricette più elegante
- caricamento immagini PDF più robusto:
  - normalizza `www` / non-`www`
  - prova fetch
  - fallback canvas
  - rileva formato PNG/JPEG/WEBP


## v27d PDF giornaliero

- Prima pagina: overview settimanale
- Poi 7 pagine: una per ogni giorno della settimana
- In ogni pagina giornaliera: card grandi per colazione, pranzo, spuntino, cena
- Ultima sezione: ingredienti ricetta per ricetta con immagini grandi
- Mantiene il fix immagini PDF del v27c

## v27e ASCII PDF fix

Fix di sicurezza per `Uncaught SyntaxError: Invalid or unexpected token`:
- `weekly-menu.js` riscritto/salvato in UTF-8 ASCII-safe
- rimossi emoji/caratteri speciali dal sorgente JS
- PDF giornaliero v27d mantenuto
- console marker: `weekly-menu v27e ascii pdf fix loaded`

## v27f syntax fix

Corretto errore JS:
- stringa `ingredientLines.join("\n")` non spezzata su due righe
- regex `replace(/\n+/g, " ")` non spezzata su due righe
- console marker: `weekly-menu v27f syntax fix loaded`

## v27g multi-ricetta per pasto

- Ogni slot pranzo/cena/colazione/spuntino ora può contenere più ricette.
- Il vecchio indice unico `ux_weekly_menu_items_slot` viene rimosso automaticamente.
- Nel planner gli slot vuoti sono compatti.
- Nel PDF giornaliero vengono mostrati solo i pasti compilati.
- Se un pasto ha più ricette, il PDF mostra la principale con indicazione delle altre.

## v27h note menu-specifiche nel PDF

- Nel modal di scelta ricetta c'e un campo "Nota per questo menu".
- La nota viene salvata nello slot del menu, non nella ricetta.
- Nel planner la nota appare sotto la ricetta aggiunta.
- Nel PDF giornaliero e nella sezione finale si usano le note del menu al posto della descrizione della ricetta.
