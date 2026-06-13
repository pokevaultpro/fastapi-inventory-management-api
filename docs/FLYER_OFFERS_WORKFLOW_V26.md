# SmartGrocery v26 — Workflow volantini scalabile

## Obiettivo

Non importare più i volantini direttamente dentro `Products`.

La nuova logica è:

```txt
Products = catalogo stabile
Flyers = volantino settimanale
FlyerOffers = offerte temporanee del volantino
ProductAliases = regole di associazione imparate
```

## Perché

Nel volantino spesso il prezzo è implicito come offerta, anche senza prezzo precedente.

Esempio:

```txt
Anguria 0,69 €/kg
```

Non è corretto salvarla come `discounted_price`, perché manca il prezzo precedente.
È meglio salvarla come:

```txt
FlyerOffer.offer_price = 0.69
FlyerOffer.status = published
```

e nel frontend mostrarla come:

```txt
Offerta volantino
0,69 €/kg
Valida fino al 27 giugno
```

## Cosa aggiunge

### Tabelle nuove

```txt
flyers
flyer_offers
product_aliases
```

### Campi extra su Products

La patch aggiunge anche i campi che potevano mancare:

```txt
brand
price_type
price_unit
flyer_page
flyer_valid_from
flyer_valid_to
flyer_source
flyer_source_url
is_lidl_plus
offer_note
discount_percent
```

## Import ZIP

Nuovo endpoint:

```txt
POST /admin/flyer-offers/import-zip
```

Accetta lo stesso formato ZIP:

```txt
products.json
product_images/*.jpg
```

Ma adesso NON crea Products subito.

Crea invece:

```txt
flyer_offers in draft
```

con:

```txt
auto_matched
needs_review
new_product_suggestion
```

## Matching automatico

Il sistema prova ad associare ogni riga del volantino al catalogo usando:

```txt
alias imparati
nome normalizzato
brand
unità/formato
categoria
supermercato
```

Soglie:

```txt
>= 90% auto_matched
>= 68% needs_review
< 68% new_product_suggestion
```

## Admin

In `admin.html` aggiunge la sezione:

```txt
Offerte volantini
```

Da lì puoi:

```txt
importare ZIP in bozza
vedere statistiche auto/dubbi/nuovi
approvare tutti gli auto-match
associare manualmente i dubbi
creare Product solo per i veri nuovi
scartare righe sbagliate
pubblicare offerte
```

## Endpoint admin

```txt
GET  /admin/flyer-offers/debug
POST /admin/flyer-offers/import-zip
GET  /admin/flyer-offers/flyers
GET  /admin/flyer-offers/flyers/{flyer_id}/offers
POST /admin/flyer-offers/flyers/{flyer_id}/approve-auto
POST /admin/flyer-offers/flyers/{flyer_id}/publish
POST /admin/flyer-offers/offers/{offer_id}/associate
POST /admin/flyer-offers/offers/{offer_id}/create-product
POST /admin/flyer-offers/offers/{offer_id}/reject
GET  /admin/flyer-offers/products/search
```

## Endpoint pubblici per frontend

```txt
GET /flyer-offers/active
GET /flyer-offers/product/{product_id}
```

Questi servono per mostrare le offerte attive nel sito.

## Installazione

Dalla root:

```powershell
python install_flyer_offers_workflow_v26.py
```

Poi:

```txt
commit
push
redeploy Render
```

Su Render Shell, se serve:

```bash
python scripts/migrate_flyer_offers_v26.py
```

## SiteGround

Carica:

```txt
frontend/admin.html
frontend/js/flyer-offers-admin-v26.js
frontend/css/flyer-offers-admin-v26.css
```

Poi:

```txt
Ctrl + F5
```

## Uso consigliato

1. Vai in Admin → Offerte volantini.
2. Carica `conad_import_products_2026_06_15_27.zip`.
3. Guarda i conteggi:
   - auto-match
   - da controllare
   - nuovi prodotti
4. Clicca `Approva auto-match`.
5. Controlla solo i dubbi.
6. Per nuovi prodotti veri, clicca `Crea prodotto`.
7. Clicca `Pubblica approvate`.

## Nota

Questa patch crea il backend e admin workflow.
Il passaggio successivo è collegare la pagina prodotti/lista spesa a:

```txt
GET /flyer-offers/active
```

per visualizzare il badge "Offerta volantino" anche quando non esiste `discounted_price < original_price`.
