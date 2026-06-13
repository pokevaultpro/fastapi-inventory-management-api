from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


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
        raise RuntimeError("Non trovo supermercati con nome contenente Conad.")

    id_list = ", ".join(str(int(x)) for x in conad_ids)
    conad_filter = f"{q('supermarket_id')} IN ({id_list})"

    offer_filters: list[str] = []
    params: dict[str, Any] = {"valid_from": valid_from, "valid_to": valid_to}

    if "flyer_page" in product_columns:
        offer_filters.append(f"{q('flyer_page')} IS NOT NULL")
    if "flyer_valid_from" in product_columns:
        offer_filters.append(f"{q('flyer_valid_from')} = :valid_from")
    if "flyer_valid_to" in product_columns:
        offer_filters.append(f"{q('flyer_valid_to')} = :valid_to")
    if "flyer_source" in product_columns:
        offer_filters.append(f"lower(COALESCE({q('flyer_source')}, '')) LIKE '%conad%'")

    if not offer_filters:
        raise RuntimeError("Products non ha campi flyer utili per individuare import Conad.")

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
    for optional in [
        "brand",
        "flyer_page",
        "flyer_valid_from",
        "flyer_valid_to",
        "flyer_source",
        "price_type",
        "price_unit",
        "offer_note",
    ]:
        if optional in product_columns:
            selected.append(optional)

    rows = conn.execute(
        text(f"""
            SELECT {', '.join(q(c) for c in selected)}
            FROM {q('products')}
            WHERE {where_sql}
            ORDER BY {q('id')}
        """),
        params,
    ).mappings().all()
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
                deps.append({"table": table_name, "column": constrained_cols[0]})

    known = [
        ("cart", "product_id"),
        ("cart_items", "product_id"),
        ("favorites", "product_id"),
        ("recipe_items", "product_id"),
        ("shopping_history_items", "product_id"),
        ("history_items", "product_id"),
        ("flyer_offers", "product_id"),
        ("flyer_offers", "suggested_product_id"),
        ("product_aliases", "product_id"),
    ]
    tables = set(inspector.get_table_names())
    for table_name, column in known:
        if table_name in tables:
            cols = columns_for(inspector, table_name)
            if column in cols and not any(d["table"] == table_name and d["column"] == column for d in deps):
                deps.append({"table": table_name, "column": column})

    return deps


def bind_ids(ids: list[int], prefix: str = "id") -> tuple[str, dict[str, int]]:
    params = {f"{prefix}{i}": int(value) for i, value in enumerate(ids)}
    placeholders = ", ".join(f":{key}" for key in params)
    return placeholders, params


def count_dependencies(conn, deps: list[dict[str, str]], product_ids: list[int]) -> list[dict[str, Any]]:
    if not product_ids:
        return []

    placeholders, params = bind_ids(product_ids)
    result: list[dict[str, Any]] = []

    for dep in deps:
        count = conn.execute(
            text(f"SELECT COUNT(*) FROM {q(dep['table'])} WHERE {q(dep['column'])} IN ({placeholders})"),
            params,
        ).scalar() or 0
        result.append({"table": dep["table"], "column": dep["column"], "rows": int(count)})

    return result


def delete_image_files(rows: list[dict[str, Any]], project_root: Path) -> int:
    deleted = 0
    root = project_root.resolve()

    for row in rows:
        image = row.get("image")
        if not image or not isinstance(image, str):
            continue
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

    # For flyer_offers, do not delete the offer row if only product_id/suggested_product_id points
    # to a product we are deleting. Null it instead, so draft/published offer history survives.
    for dep in deps:
        if dep["table"] == "flyer_offers" and dep["column"] in {"product_id", "suggested_product_id"}:
            result = conn.execute(
                text(f"UPDATE {q(dep['table'])} SET {q(dep['column'])}=NULL WHERE {q(dep['column'])} IN ({placeholders})"),
                params,
            )
            dependency_deleted.append({
                "table": dep["table"],
                "column": dep["column"],
                "action": "set_null",
                "rows_deleted": int(result.rowcount or 0),
            })
            continue

        sql = f"DELETE FROM {q(dep['table'])} WHERE {q(dep['column'])} IN ({placeholders})"
        result = conn.execute(text(sql), params)
        dependency_deleted.append({
            "table": dep["table"],
            "column": dep["column"],
            "action": "delete",
            "rows_deleted": int(result.rowcount or 0),
        })

    product_result = conn.execute(
        text(f"DELETE FROM {q('products')} WHERE {q('id')} IN ({placeholders})"),
        params,
    )

    return {
        "dependency_deleted": dependency_deleted,
        "products_deleted": int(product_result.rowcount or 0),
    }


def preview_cleanup(engine: Engine, *, valid_from: str = "2026-06-15", valid_to: str = "2026-06-27") -> dict[str, Any]:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "products" not in tables:
        raise RuntimeError("Non trovo tabella products.")
    if "supermarkets" not in tables:
        raise RuntimeError("Non trovo tabella supermarkets.")

    product_columns = columns_for(inspector, "products")
    if "supermarket_id" not in product_columns:
        raise RuntimeError("products non ha supermarket_id.")

    with engine.begin() as conn:
        conad_ids = get_conad_supermarket_ids(conn)
        candidates = find_candidates(conn, product_columns, conad_ids, valid_from, valid_to)
        product_ids = [int(row["id"]) for row in candidates]
        deps = dependency_tables(inspector)
        dep_counts = count_dependencies(conn, deps, product_ids)

    return {
        "mode": "preview",
        "valid_from": valid_from,
        "valid_to": valid_to,
        "conad_supermarket_ids": conad_ids,
        "candidate_count": len(candidates),
        "first_candidates": candidates[:30],
        "dependency_counts": dep_counts,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def execute_cleanup(
    engine: Engine,
    *,
    valid_from: str = "2026-06-15",
    valid_to: str = "2026-06-27",
    delete_images: bool = False,
    project_root: Path | None = None,
) -> dict[str, Any]:
    inspector = inspect(engine)
    product_columns = columns_for(inspector, "products")

    with engine.begin() as conn:
        conad_ids = get_conad_supermarket_ids(conn)
        candidates = find_candidates(conn, product_columns, conad_ids, valid_from, valid_to)
        product_ids = [int(row["id"]) for row in candidates]
        deps = dependency_tables(inspector)
        dep_counts = count_dependencies(conn, deps, product_ids)

        if not product_ids:
            return {
                "mode": "execute",
                "valid_from": valid_from,
                "valid_to": valid_to,
                "candidate_count": 0,
                "products_deleted": 0,
                "dependency_counts": dep_counts,
                "dependency_deleted": [],
                "images_deleted": 0,
            }

        result = delete_rows(conn, deps, product_ids)

    images_deleted = 0
    if delete_images:
        images_deleted = delete_image_files(candidates, project_root or Path.cwd())

    return {
        "mode": "execute",
        "valid_from": valid_from,
        "valid_to": valid_to,
        "candidate_count": len(candidates),
        "first_deleted": candidates[:30],
        "dependency_counts": dep_counts,
        "dependency_deleted": result["dependency_deleted"],
        "products_deleted": result["products_deleted"],
        "images_deleted": images_deleted,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
