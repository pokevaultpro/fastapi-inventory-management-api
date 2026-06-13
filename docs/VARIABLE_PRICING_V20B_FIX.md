# SmartGrocery v20b — Fix salvataggio tipo prezzo

## Problema

Quando cambiavi un prodotto da:

```txt
Prezzo fisso
```

a:

```txt
Al peso / al kg
```

la pagina diceva "prodotto aggiornato", ma poi restava fisso.

Causa più probabile: il backend stava ignorando `price_type` perché il model `Products` deployato su Render non aveva ancora:

```txt
price_type
price_unit
```

Questa patch aggiunge controlli espliciti: se il backend non ha quei campi, non fa più finta di salvare, ma restituisce errore chiaro.

## Installazione

Dalla root del progetto:

```powershell
python install_variable_pricing_v20b.py
python scripts\force_variable_pricing_model_v20b.py
```

Poi fai commit/push/deploy del backend su Render.

## Controllo Render

In Swagger online esegui:

```txt
GET /admin/debug/products-model
```

Deve dare:

```json
{
  "has_price_type": true,
  "has_price_unit": true,
  "db_has_price_type": true,
  "db_has_price_unit": true
}
```

Se `has_price_type` è false:
Render non sta usando il model aggiornato.

Se `has_price_type` è true ma `db_has_price_type` è false:
il codice è aggiornato ma il DB non ha ancora la colonna. Esegui su Render:

```bash
python scripts/migrate_variable_pricing_v20.py
```

## Test rapido

Modifica un prodotto:

```txt
Tipo prezzo: al peso / al kg
Unità prezzo: kg
Prezzo originale: 1.59
```

Salva.

Poi ricarica admin.html con Ctrl+F5. Nella tabella deve comparire:

```txt
al peso · kg
```
