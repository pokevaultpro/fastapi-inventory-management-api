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
