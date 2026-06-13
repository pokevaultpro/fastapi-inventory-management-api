# SmartGrocery v20 — Prodotti al peso e prezzo manuale

## Obiettivo

Gestire prodotti come:

- frutta e verdura al kg;
- carne/pesce/gastronomia al kg;
- prodotti senza prezzo fisso, dove inserisci il prezzo finale a mano nella lista.

## Nuovi campi prodotto

In `Products`:

```txt
price_type: fixed | weight | manual
price_unit: pz | kg | g | L ...
```

Significato:

```txt
fixed  = prodotto normale, prezzo per pezzo/confezione
weight = prodotto al peso, original_price è prezzo per kg/unità
manual = prezzo finale da inserire nella lista
```

## Nuovi campi carrello

In `Cart`:

```txt
estimated_weight
actual_weight
manual_price
```

Logica del totale:

```txt
se manual_price esiste → usa quello
altrimenti se price_type = weight → prezzo al kg × peso reale/stimato
altrimenti → prezzo unitario × quantità
```

## Nuovi campi storico

In `ShoppingHistoryItem`:

```txt
price_type
price_unit
estimated_weight
actual_weight
weight_bought
price_per_unit_snapshot
final_price_paid
was_manual_price
manual_price
```

Così nello storico puoi sapere peso, prezzo al kg snapshot e prezzo finale pagato.

## Installazione

Dalla root del progetto:

```powershell
python install_variable_pricing_v20.py
python scripts\force_variable_pricing_model_v20.py
```

Poi fai deploy backend su Render.

Se vuoi forzare la migrazione DB su Render:

```bash
python scripts/migrate_variable_pricing_v20.py
```

## Frontend da caricare su SiteGround

Carica almeno:

```txt
frontend/admin.html
frontend/css/admin.css
frontend/css/products.css
frontend/css/shopping.css
frontend/css/history.css
frontend/js/admin.js
frontend/js/admin-role.js
frontend/js/products.js
frontend/js/modal-function.js
frontend/js/shopping.js
frontend/history.html
frontend/js/history.js
frontend/js/history-all.js
frontend/js/history-products.js
```

Poi fai Ctrl+F5.

## Uso pratico

### Prodotto normale

```txt
Tipo prezzo: fisso
Prezzo: 1.29
Unità prezzo: pz
```

### Banane al kg

```txt
Tipo prezzo: al peso / al kg
Prezzo: 1.59
Unità prezzo: kg
```

Nella lista puoi impostare:

```txt
peso stimato
peso reale
prezzo finale opzionale
```

### Prodotto manuale

```txt
Tipo prezzo: manuale
Prezzo: 0
Unità prezzo: pz
```

Nella lista devi inserire:

```txt
prezzo finale
```

prima di finalizzare.
