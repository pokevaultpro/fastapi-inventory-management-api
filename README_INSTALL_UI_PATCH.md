# Installazione patch grafica prodotti

1. Estrai questo ZIP nella root del progetto.
2. Da terminale, nella root del progetto:

```bash
python install_ui_products_patch.py
```

3. Riavvia FastAPI:

```bash
uvicorn app.main:app --reload
```

4. Reimporta lo ZIP Lidl completo da:

```txt
POST /flyer-catalog/import-zip
```

con:

```txt
update_existing = true
save_archive_folder = true
```

5. Apri `products.html` e fai hard refresh:

```txt
Ctrl + F5
```

## Perché reimportare lo ZIP Lidl?

La grafica nuova può mostrare `Volantino p.X`, Lidl Plus e validità offerta solo se quei dati sono nel database. La patch aggiorna l'importer per salvarli, quindi devi reimportare lo ZIP catalogo.
