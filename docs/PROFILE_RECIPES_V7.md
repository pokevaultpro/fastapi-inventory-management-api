# SmartGrocery - Profilo e Ricette v7

## Cosa aggiunge

### Profilo
- Pagina `profile.html` responsive desktop/mobile.
- Endpoint `GET /profile/summary` con riepilogo utente, carrello, storico, ricette e categorie più comprate.
- Endpoint `PUT /profile` per aggiornare nome, cognome e username.

### Ricette personali
- Pagina `recipes.html` responsive.
- Nuovi endpoint `/smart-recipes`.
- Creazione ricette con immagine/URL, descrizione, istruzioni, porzioni, tempo di preparazione.
- Ingredienti selezionati dal catalogo prodotti, con quantità ricetta e quantità da aggiungere al carrello.
- Dettaglio ricetta con prezzo totale stimato.
- Aggiunta ricetta alla lista della spesa scegliendo cosa includere/escludere.
- Suggerimento di alternative più economiche quando trova prodotti simili in altri supermercati.

### Ricetta del giorno
- Endpoint `GET /smart-recipes/daily/today`.
- Prova a leggere una ricetta gratuita da TheMealDB e ad abbinarne gli ingredienti al catalogo prodotti.
- Se la fonte online non risponde, usa una ricetta fallback locale.
- Endpoint `POST /smart-recipes/daily/add-to-cart` per aggiungere i prodotti trovati al carrello.

## Bug validità volantino

La patch aggiunge i campi mancanti al modello `Products`:

- `flyer_page`
- `flyer_valid_from`
- `flyer_valid_to`
- `flyer_source`
- `is_lidl_plus`
- `discount_percent`
- `offer_note`

Prima il database poteva avere le colonne, ma il modello SQLAlchemy non le salvava davvero. Dopo questa patch bisogna reimportare lo ZIP Lidl completo con:

```txt
POST /flyer-catalog/import-zip
update_existing = true
save_archive_folder = true
```

Così la UI non mostrerà più `Data del volantino non salvata` sui prodotti importati dal volantino.

## Installazione

Estrai lo ZIP nella root del progetto e lancia:

```bash
python install_profile_recipes_v7.py
```

Poi:

```bash
uvicorn app.main:app --reload
```

Infine fai hard refresh nel browser: `Ctrl + F5`.

## Limiti noti

- L'immagine ricetta è per ora un URL/path testuale. Su Render conviene non salvare immagini nel filesystem effimero: meglio usare SiteGround o un bucket.
- La ricetta del giorno da internet usa ingredienti spesso in inglese; il matching al catalogo italiano è euristico e migliorerà aggiungendo alias.
