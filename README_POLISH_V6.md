# SmartGrocery Polish v6

Questa patch corregge e migliora:

- storico su mobile;
- bottom bar mobile con icona Storico;
- grafico spesa nel tempo con punti e tooltip;
- grafico supermercati stabile quando cambi range;
- home page nuova per desktop/mobile;
- cuore preferiti chiaramente cliccabile;
- validità dei prodotti da volantino;
- scadenza automatica degli sconti dopo fine validità;
- finalizzazione carrello e restore storico usano prezzo attuale, quindi non tengono sconti scaduti.

## Installazione

Estrai questo ZIP nella root del progetto, poi:

```bash
python install_smartgrocery_polish_v6.py
```

Riavvia:

```bash
uvicorn app.main:app --reload
```

Poi browser:

```txt
Ctrl + F5
```

## Import Lidl

Se prima vedevi "validità non indicata", reimporta lo ZIP catalogo completo online/locale:

```txt
POST /flyer-catalog/import-zip
update_existing=true
```

Lo ZIP completo Lidl include già validità 2026-06-11 → 2026-06-17.
