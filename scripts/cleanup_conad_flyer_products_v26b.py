from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def q(name: str) -> str:
    """Quote SQL identifiers for PostgreSQL/SQLite."""
    return '"' + name.replace('"', '""') + '"'


def bind_ids(ids: list[int], prefix: str = "id") -> tuple[str, dict[str, int]]:
    params = {f"{prefix}{i}": int(value) for i, value in enumerate(ids)}
    placeholders = ", ".join(f":{key}" for key in params)
    return placeholders, params


def columns_for(inspector, table_name: str) -> set[str]:
    if table_name not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def get_conad_supermarket_ids(conn) -> list[int]:
    rows = conn.execute(
        text("SELECT id, name FROM supermarkets WHERE lower(name) LIKE '%conad%' ORDER BY id")
    ).mappings().all()
    return [int(row["id"]) for row in rows]


def build_candidate_where(product_columns: set[str], conad_ids: list[int], valid_from: str, valid_to: str) -> tuple[str, dict[str, Any]]:
    if not conad_ids:
        raise RuntimeError("Non trovo nessun supermercato con nome contenente 'Conad'. Mi fermo per sicurezza.")

    id_list = ", ".join(str(int(x)) for x in conad_ids)
    conad_filter = f"{q('supermarket_id')} IN ({id_list})"

    offer_filters: list[str] = []
    params: dict[str, Any] = {
        "valid_from": valid_from,
        "valid_to": valid_to,
    }

    if "flyer_page" in product_columns:
        offer_filters.append(f"{q('flyer_page')} IS NOT NULL")

    if "flyer_valid_from" in product_columns:
        offer_filters.append(f"{q('flyer_valid_from')} = :valid_from")

    if "flyer_valid_to" in product_columns:
        offer_filters.append(f"{q('flyer_valid_to')} = :valid_to")

    if "flyer_source" in product_columns:
        offer_filters.append(f"lower(COALESCE({q('flyer_source')}, '')) LIKE '%conad%'")

    if not offer_filters:
        raise RuntimeError(
            "La tabella products non ha campi flyer_page/flyer_valid_from/flyer_valid_to/flyer_source. "
            "Mi fermo per sicurezza."
        )

    return f"{conad_filter} AND ({' OR '.join(offer_filters)})", params


def find_candidates(conn, product_columns: set[str], conad_ids: list[int], valid_from: str, valid_to: str) -> list[dict[str, Any]]:
    where_sql, params = build_candidate_where(product_columns, conad_ids, valid_from, valid_to)

    selected = [
        "id",
        "name",
        "category",
        "unit",
        "original_price",
        "discounted_price",
        "image",
        "supermarket_id",
    ]
    for optional in ["brand", "flyer_page", "flyer_valid_from", "flyer_valid_to", "flyer_source", "price_type", "price_unit", "offer_note"]:
        if optional in product_columns:
            selected.append(optional)

    sql = f"""
        SELECT {', '.join(q(c) for c in selected)}
        FROM {q('products')}
        WHERE {where_sql}
        ORDER BY {q('id')}
    """
    rows = conn.execute(text(sql), params).mappings().all()
    return [dict(row) for row in rows]


def dependency_tables(inspector) -> list[dict[str, str]]:
    deps: list[dict[str, str]] = []

    for table_name in inspector.get_table_names():
        if table_name == "products":
            continue

        for fk in inspector.get_foreign_keys(table_name):
            referred = fk.get("referred_table")
            referred_cols = fk.get("referred_columns") or []
            constrained_cols = fk.get("constrained_columns") or []

            if referred == "products" and "id" in referred_cols and constrained_cols:
                deps.append({
                    "table": table_name,
                    "column": constrained_cols[0],
                })

    # Some older SQLite projects may not expose all FK metadata; include common names if present.
    known = [
        ("cart", "product_id"),
        ("cart_items", "product_id"),
        ("favorites", "product_id"),
        ("recipe_items", "product_id"),
        ("shopping_history_items", "product_id"),
        ("history_items", "product_id"),
    ]

    tables = set(inspector.get_table_names())
    for table_name, column in known:
        if table_name in tables:
            cols = columns_for(inspector, table_name)
            if column in cols and not any(d["table"] == table_name and d["column"] == column for d in deps):
                deps.append({"table": table_name, "column": column})

    return deps


def count_dependencies(conn, deps: list[dict[str, str]], product_ids: list[int]) -> list[dict[str, Any]]:
    if not product_ids:
        return []

    placeholders, params = bind_ids(product_ids)
    result: list[dict[str, Any]] = []

    for dep in deps:
        sql = f"SELECT COUNT(*) FROM {q(dep['table'])} WHERE {q(dep['column'])} IN ({placeholders})"
        count = conn.execute(text(sql), params).scalar() or 0
        result.append({
            "table": dep["table"],
            "column": dep["column"],
            "rows": int(count),
        })

    return result


def write_report(rows: list[dict[str, Any]], report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = report_dir / f"conad_flyer_products_cleanup_{timestamp}.csv"

    fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else ["id", "name"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return path


def delete_image_files(rows: list[dict[str, Any]]) -> int:
    deleted = 0
    root = PROJECT_ROOT.resolve()

    for row in rows:
        image = row.get("image")
        if not image or not isinstance(image, str):
            continue

        # Only delete local static images. Never touch remote URLs.
        if image.startswith("http://") or image.startswith("https://"):
            continue

        rel = image.lstrip("/")
        candidate = (root / rel).resolve()

        try:
            if root not in candidate.parents and candidate != root:
                continue
            if candidate.exists() and candidate.is_file():
                candidate.unlink()
                deleted += 1
        except Exception:
            pass

    return deleted


def delete_rows(conn, deps: list[dict[str, str]], product_ids: list[int]) -> dict[str, Any]:
    placeholders, params = bind_ids(product_ids)
    dependency_deleted: list[dict[str, Any]] = []

    for dep in deps:
        sql = f"DELETE FROM {q(dep['table'])} WHERE {q(dep['column'])} IN ({placeholders})"
        result = conn.execute(text(sql), params)
        dependency_deleted.append({
            "table": dep["table"],
            "column": dep["column"],
            "rows_deleted": int(result.rowcount or 0),
        })

    product_sql = f"DELETE FROM {q('products')} WHERE {q('id')} IN ({placeholders})"
    product_result = conn.execute(text(product_sql), params)

    return {
        "dependency_deleted": dependency_deleted,
        "products_deleted": int(product_result.rowcount or 0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run/delete accidental Conad flyer products imported directly into Products."
    )
    parser.add_argument("--execute", action="store_true", help="Esegue davvero la cancellazione. Senza questo flag fa solo dry-run.")
    parser.add_argument("--delete-images", action="store_true", help="Cancella anche i file immagine locali collegati ai prodotti.")
    parser.add_argument("--valid-from", default="2026-06-15")
    parser.add_argument("--valid-to", default="2026-06-27")
    args = parser.parse_args()

    from app.database import engine

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "products" not in tables:
        raise RuntimeError("Non trovo la tabella products.")
    if "supermarkets" not in tables:
        raise RuntimeError("Non trovo la tabella supermarkets.")

    product_columns = columns_for(inspector, "products")
    if "supermarket_id" not in product_columns:
        raise RuntimeError("products non ha supermarket_id. Mi fermo per sicurezza.")

    with engine.begin() as conn:
        conad_ids = get_conad_supermarket_ids(conn)
        candidates = find_candidates(conn, product_columns, conad_ids, args.valid_from, args.valid_to)
        product_ids = [int(row["id"]) for row in candidates]
        deps = dependency_tables(inspector)
        dep_counts = count_dependencies(conn, deps, product_ids)
        report_path = write_report(candidates, PROJECT_ROOT / "cleanup_reports")

        print()
        print("=== Cleanup Conad prodotti importati da volantino ===")
        print(f"Conad supermarket IDs: {conad_ids}")
        print(f"Validità target: {args.valid_from} -> {args.valid_to}")
        print(f"Prodotti candidati: {len(candidates)}")
        print(f"Report CSV: {report_path}")
        print()

        if candidates[:10]:
            print("Primi candidati:")
            for row in candidates[:10]:
                print(f"- #{row.get('id')} {row.get('name')} | pag={row.get('flyer_page')} | valid={row.get('flyer_valid_from')}->{row.get('flyer_valid_to')}")
            if len(candidates) > 10:
                print(f"... altri {len(candidates) - 10}")
            print()

        print("Righe collegate che verrebbero cancellate prima dei prodotti:")
        if dep_counts:
            for dep in dep_counts:
                if dep["rows"]:
                    print(f"- {dep['table']}.{dep['column']}: {dep['rows']}")
        else:
            print("- nessuna dependency rilevata")
        print()

        if not args.execute:
            print("DRY-RUN: non ho cancellato nulla.")
            print("Per cancellare davvero:")
            print("python scripts/cleanup_conad_flyer_products_v26b.py --execute")
            print()
            print("Per cancellare anche i file immagine locali:")
            print("python scripts/cleanup_conad_flyer_products_v26b.py --execute --delete-images")
            return

        if not product_ids:
            print("Nessun prodotto da cancellare.")
            return

        result = delete_rows(conn, deps, product_ids)
        images_deleted = delete_image_files(candidates) if args.delete_images else 0

        print("CANCELLAZIONE COMPLETATA")
        for dep in result["dependency_deleted"]:
            if dep["rows_deleted"]:
                print(f"- cancellate {dep['rows_deleted']} righe da {dep['table']}")
        print(f"- prodotti cancellati: {result['products_deleted']}")
        print(f"- immagini locali cancellate: {images_deleted}")
        print()
        print("Ora puoi usare il nuovo workflow v26: importa ZIP in Offerte volantini, non più direttamente in Products.")


if __name__ == "__main__":
    main()
