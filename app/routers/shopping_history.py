from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
import re
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from app.database import SessionLocal
from app.routers.auth import get_current_user
from app.models import Users, ShoppingHistory, ShoppingHistoryItem, Cart, Products

router = APIRouter(
    prefix="/shopping-history",
    tags=["shopping-history"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class HistoryRestoreResponse(BaseModel):
    history_id: int
    restored_count: int
    merged_count: int
    missing_count: int
    previous_total: float
    current_total: float
    total_delta: float
    price_changes: list[dict]
    missing: list[dict]
    restored_product_ids: list[int]
    message: str


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _round_money(value: float | int | None) -> float:
    return round(float(value or 0), 2)


def _parse_product_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")[:10])
    except ValueError:
        return None


def _parse_source_dates(value: str | None) -> tuple[str | None, str | None]:
    text = str(value or "")
    match = re.search(r"(\d{4})[_-](\d{2})[_-](\d{2}).*?(\d{4})[_-](\d{2})[_-](\d{2})", text)
    if not match:
        return None, None
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}", f"{match.group(4)}-{match.group(5)}-{match.group(6)}"


def _product_offer_is_active(product: Products) -> bool:
    valid_to = getattr(product, "flyer_valid_to", None)
    if not valid_to:
        _, valid_to = _parse_source_dates(getattr(product, "flyer_source", None))
    end = _parse_product_date(valid_to)
    if end is None:
        return True
    return end.date() >= datetime.utcnow().date()


def _product_current_price(product: Products) -> float:
    if _product_offer_is_active(product) and product.discounted_price is not None:
        return float(product.discounted_price)
    return float(product.original_price)


def _history_owned_query(db: Session, owner_id: int):
    return db.query(ShoppingHistory).filter(ShoppingHistory.user_id == owner_id)


def _ensure_user(db: Session, owner_id: int) -> Users:
    user_model = db.query(Users).filter(Users.id == owner_id).first()
    if not user_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_model


def _filter_histories_by_days(histories: list[ShoppingHistory], days: int | None) -> list[ShoppingHistory]:
    if not days:
        return histories
    cutoff = datetime.utcnow() - timedelta(days=days)
    return [h for h in histories if (_parse_datetime(h.created_at) or datetime.min) >= cutoff]


@router.get("", status_code=status.HTTP_200_OK)
async def get_shopping_history(
    user: user_dependency,
    db: db_dependency,
    limit: Optional[int] = Query(default=None, gt=0, le=200),
):
    owner_id = user.get("id")
    _ensure_user(db, owner_id)

    query = _history_owned_query(db, owner_id).order_by(ShoppingHistory.created_at.desc())
    if limit is not None:
        query = query.limit(limit)
    return query.all()


@router.get("/recent", status_code=status.HTTP_200_OK)
async def get_recent_shopping_histories(
    user: user_dependency,
    db: db_dependency,
    limit: int = Query(default=5, gt=0, le=20),
):
    owner_id = user.get("id")
    _ensure_user(db, owner_id)

    histories = (
        _history_owned_query(db, owner_id)
        .order_by(ShoppingHistory.created_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for history in histories:
        preview_items = (
            db.query(ShoppingHistoryItem)
            .filter(ShoppingHistoryItem.history_id == history.id)
            .limit(5)
            .all()
        )
        result.append({
            "id": history.id,
            "created_at": history.created_at,
            "total_price": _round_money(history.total_price),
            "total_items": history.total_items,
            "preview_items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "name": item.name,
                    "image": item.image,
                    "quantity": item.quantity,
                    "price_paid": _round_money(item.price_paid),
                    "category": item.category,
                    "supermarket_name": item.supermarket_name,
                }
                for item in preview_items
            ],
        })
    return result


@router.get("/stats", status_code=status.HTTP_200_OK)
@router.get("/stats/summary", status_code=status.HTTP_200_OK)
async def get_shopping_history_stats(
    user: user_dependency,
    db: db_dependency,
    days: Optional[int] = Query(default=None, gt=0, le=3650),
):
    owner_id = user.get("id")
    _ensure_user(db, owner_id)

    histories = (
        _history_owned_query(db, owner_id)
        .order_by(ShoppingHistory.created_at.asc())
        .all()
    )
    histories = _filter_histories_by_days(histories, days)

    history_ids = [h.id for h in histories]
    if not history_ids:
        return {
            "overview": {
                "trips_count": 0,
                "total_spent": 0,
                "total_items": 0,
                "average_trip": 0,
                "average_item_price": 0,
                "discounted_lines": 0,
                "estimated_savings": 0,
            },
            "monthly": [],
            "category_breakdown": [],
            "supermarket_breakdown": [],
            "top_products": [],
            "latest": [],
            "days": days,
        }

    items = (
        db.query(ShoppingHistoryItem)
        .filter(ShoppingHistoryItem.history_id.in_(history_ids))
        .all()
    )

    history_by_id = {h.id: h for h in histories}

    total_spent = sum(float(h.total_price or 0) for h in histories)
    total_items = sum(int(h.total_items or 0) for h in histories)
    trips_count = len(histories)
    average_trip = total_spent / trips_count if trips_count else 0
    average_item_price = total_spent / total_items if total_items else 0

    monthly: dict[str, dict] = defaultdict(lambda: {"period": "", "total": 0.0, "trips": 0, "items": 0})
    for history in histories:
        dt = _parse_datetime(history.created_at)
        period = dt.strftime("%Y-%m") if dt else "Sconosciuto"
        monthly[period]["period"] = period
        monthly[period]["total"] += float(history.total_price or 0)
        monthly[period]["trips"] += 1
        monthly[period]["items"] += int(history.total_items or 0)

    category_stats: dict[str, dict] = defaultdict(lambda: {"category": "", "total": 0.0, "quantity": 0, "lines": 0})
    supermarket_stats: dict[str, dict] = defaultdict(lambda: {"supermarket": "", "total": 0.0, "quantity": 0, "lines": 0})
    product_stats: dict[str, dict] = defaultdict(lambda: {"name": "", "total": 0.0, "quantity": 0, "lines": 0, "image": None, "category": None})

    estimated_savings = 0.0
    discounted_lines = 0

    for item in items:
        qty = int(item.quantity or 1)
        line_total = float(item.price_paid or 0) * qty

        category = item.category or "Senza categoria"
        category_stats[category]["category"] = category
        category_stats[category]["total"] += line_total
        category_stats[category]["quantity"] += qty
        category_stats[category]["lines"] += 1

        supermarket = item.supermarket_name or "N/D"
        supermarket_stats[supermarket]["supermarket"] = supermarket
        supermarket_stats[supermarket]["total"] += line_total
        supermarket_stats[supermarket]["quantity"] += qty
        supermarket_stats[supermarket]["lines"] += 1

        product_key = f"{item.name}|{item.unit or ''}|{item.supermarket_name or ''}"
        product_stats[product_key]["name"] = item.name
        product_stats[product_key]["total"] += line_total
        product_stats[product_key]["quantity"] += qty
        product_stats[product_key]["lines"] += 1
        product_stats[product_key]["image"] = product_stats[product_key]["image"] or item.image
        product_stats[product_key]["category"] = product_stats[product_key]["category"] or item.category

        if item.was_discounted:
            discounted_lines += 1
            if item.product_id:
                product = db.query(Products).filter(Products.id == item.product_id).first()
                if product and product.original_price is not None:
                    original_subtotal = float(product.original_price) * qty
                    estimated_savings += max(0.0, original_subtotal - line_total)

    latest_histories = sorted(histories, key=lambda h: _parse_datetime(h.created_at) or datetime.min, reverse=True)[:5]
    latest = []
    for history in latest_histories:
        preview = [i for i in items if i.history_id == history.id][:5]
        latest.append({
            "id": history.id,
            "created_at": history.created_at,
            "total_price": _round_money(history.total_price),
            "total_items": history.total_items,
            "preview_items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "name": item.name,
                    "image": item.image,
                    "quantity": item.quantity,
                    "price_paid": _round_money(item.price_paid),
                    "category": item.category,
                    "supermarket_name": item.supermarket_name,
                }
                for item in preview
            ],
        })

    def sorted_rounded(values, sort_key="total", limit=None):
        rows = sorted(values, key=lambda x: x.get(sort_key, 0), reverse=True)
        if limit:
            rows = rows[:limit]
        for row in rows:
            if "total" in row:
                row["total"] = _round_money(row["total"])
        return rows

    monthly_rows = sorted(monthly.values(), key=lambda x: x["period"])
    for row in monthly_rows:
        row["total"] = _round_money(row["total"])

    return {
        "overview": {
            "trips_count": trips_count,
            "total_spent": _round_money(total_spent),
            "total_items": total_items,
            "average_trip": _round_money(average_trip),
            "average_item_price": _round_money(average_item_price),
            "discounted_lines": discounted_lines,
            "estimated_savings": _round_money(estimated_savings),
        },
        "monthly": monthly_rows,
        "category_breakdown": sorted_rounded(list(category_stats.values()), limit=10),
        "supermarket_breakdown": sorted_rounded(list(supermarket_stats.values()), limit=10),
        "top_products": sorted_rounded(list(product_stats.values()), limit=12),
        "latest": latest,
        "days": days,
    }


@router.get("/products", status_code=status.HTTP_200_OK)
async def get_all_purchased_products(
    user: user_dependency,
    db: db_dependency,
    days: Optional[int] = Query(default=None, gt=0, le=3650),
    limit: int = Query(default=500, gt=1, le=2000),
):
    owner_id = user.get("id")
    _ensure_user(db, owner_id)

    histories = (
        _history_owned_query(db, owner_id)
        .order_by(ShoppingHistory.created_at.asc())
        .all()
    )
    histories = _filter_histories_by_days(histories, days)
    history_ids = [h.id for h in histories]

    if not history_ids:
        return {
            "overview": {
                "unique_products": 0,
                "total_quantity": 0,
                "total_spent": 0,
                "average_unit_price": 0,
                "discounted_quantity": 0,
                "discounted_share": 0,
                "favorite_product": None,
                "favorite_category": None,
                "favorite_supermarket": None,
            },
            "products": [],
            "days": days,
        }

    items = (
        db.query(ShoppingHistoryItem)
        .filter(ShoppingHistoryItem.history_id.in_(history_ids))
        .all()
    )
    histories_by_id = {h.id: h for h in histories}

    products: dict[str, dict] = {}
    category_totals: dict[str, float] = defaultdict(float)
    supermarket_totals: dict[str, float] = defaultdict(float)

    total_quantity = 0
    total_spent = 0.0
    discounted_quantity = 0

    for item in items:
        qty = int(item.quantity or 1)
        unit_price = float(item.price_paid or 0)
        line_total = unit_price * qty
        total_quantity += qty
        total_spent += line_total

        if item.was_discounted:
            discounted_quantity += qty

        category = item.category or "Senza categoria"
        supermarket = item.supermarket_name or "N/D"
        category_totals[category] += line_total
        supermarket_totals[supermarket] += line_total

        history = histories_by_id.get(item.history_id)
        bought_at = history.created_at if history else None
        key = f"{item.product_id or ''}|{item.name}|{item.unit or ''}|{supermarket}"

        if key not in products:
            products[key] = {
                "product_id": item.product_id,
                "name": item.name,
                "image": item.image,
                "unit": item.unit,
                "category": category,
                "supermarket_id": item.supermarket_id,
                "supermarket_name": supermarket,
                "quantity": 0,
                "lines": 0,
                "total": 0.0,
                "average_unit_price": 0.0,
                "discounted_quantity": 0,
                "discounted_lines": 0,
                "first_bought_at": bought_at,
                "last_bought_at": bought_at,
                "last_price_paid": unit_price,
            }

        row = products[key]
        row["quantity"] += qty
        row["lines"] += 1
        row["total"] += line_total
        row["last_price_paid"] = unit_price
        if item.was_discounted:
            row["discounted_quantity"] += qty
            row["discounted_lines"] += 1

        first_dt = _parse_datetime(row["first_bought_at"])
        last_dt = _parse_datetime(row["last_bought_at"])
        bought_dt = _parse_datetime(bought_at)
        if bought_dt and (first_dt is None or bought_dt < first_dt):
            row["first_bought_at"] = bought_at
        if bought_dt and (last_dt is None or bought_dt > last_dt):
            row["last_bought_at"] = bought_at

    product_rows = []
    for row in products.values():
        row["total"] = _round_money(row["total"])
        row["average_unit_price"] = _round_money(row["total"] / row["quantity"] if row["quantity"] else 0)
        product_rows.append(row)

    product_rows.sort(key=lambda r: (-int(r["quantity"] or 0), -float(r["total"] or 0), str(r["name"] or "")))

    favorite_product = product_rows[0] if product_rows else None
    favorite_category = max(category_totals.items(), key=lambda kv: kv[1], default=(None, 0))
    favorite_supermarket = max(supermarket_totals.items(), key=lambda kv: kv[1], default=(None, 0))

    return {
        "overview": {
            "unique_products": len(product_rows),
            "total_quantity": total_quantity,
            "total_spent": _round_money(total_spent),
            "average_unit_price": _round_money(total_spent / total_quantity if total_quantity else 0),
            "discounted_quantity": discounted_quantity,
            "discounted_share": _round_money((discounted_quantity / total_quantity * 100) if total_quantity else 0),
            "favorite_product": favorite_product,
            "favorite_category": {"name": favorite_category[0], "total": _round_money(favorite_category[1])} if favorite_category[0] else None,
            "favorite_supermarket": {"name": favorite_supermarket[0], "total": _round_money(favorite_supermarket[1])} if favorite_supermarket[0] else None,
        },
        "products": product_rows[:limit],
        "days": days,
    }


@router.get("/{shopping_history_id}", status_code=status.HTTP_200_OK)
async def get_shopping_history_by_id(user: user_dependency, db: db_dependency, shopping_history_id: int = Path(gt=0)):
    shopping_history_model = (
        db.query(ShoppingHistory)
        .filter(ShoppingHistory.id == shopping_history_id)
        .filter(ShoppingHistory.user_id == user.get("id"))
        .first()
    )
    if shopping_history_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping History not found")
    return shopping_history_model


@router.get("/{shopping_history_id}/items", status_code=status.HTTP_200_OK)
async def get_shopping_history_items(user: user_dependency, db: db_dependency, shopping_history_id: int = Path(gt=0)):
    shopping_history_model = (
        db.query(ShoppingHistory)
        .filter(ShoppingHistory.id == shopping_history_id)
        .filter(ShoppingHistory.user_id == user.get("id"))
        .first()
    )
    if shopping_history_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping History not found")

    return (
        db.query(ShoppingHistoryItem)
        .filter(ShoppingHistoryItem.history_id == shopping_history_id)
        .all()
    )


@router.post("/{shopping_history_id}/restore-cart", status_code=status.HTTP_201_CREATED, response_model=HistoryRestoreResponse)
async def shopping_history_restore_cart(
    user: user_dependency,
    db: db_dependency,
    shopping_history_id: int = Path(gt=0),
    clear_existing: bool = Query(default=False),
    merge_duplicates: bool = Query(default=True),
):
    owner_id = user.get("id")
    shopping_history_model = (
        db.query(ShoppingHistory)
        .filter(ShoppingHistory.id == shopping_history_id)
        .filter(ShoppingHistory.user_id == owner_id)
        .first()
    )
    if shopping_history_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping History not found")

    shopping_history_items = (
        db.query(ShoppingHistoryItem)
        .filter(ShoppingHistoryItem.history_id == shopping_history_id)
        .all()
    )

    if clear_existing:
        db.query(Cart).filter(Cart.owner_id == owner_id).delete(synchronize_session=False)
        db.flush()

    missing_products = []
    price_changes = []
    restored_product_ids = []
    restored_count = 0
    merged_count = 0
    previous_total = 0.0
    current_total = 0.0

    for item in shopping_history_items:
        qty = int(item.quantity or 1)
        previous_line_total = float(item.price_paid or 0) * qty
        previous_total += previous_line_total

        product_model = db.query(Products).filter(Products.id == item.product_id).first() if item.product_id else None
        if product_model is None:
            missing_products.append({
                "product_id": item.product_id,
                "name": item.name,
                "quantity": qty,
                "price_paid": _round_money(item.price_paid),
                "category": item.category,
                "supermarket_name": item.supermarket_name,
            })
            continue

        current_price = _product_current_price(product_model)
        current_line_total = current_price * qty
        current_total += current_line_total

        if abs(current_price - float(item.price_paid or 0)) >= 0.01:
            price_changes.append({
                "product_id": product_model.id,
                "name": product_model.name,
                "quantity": qty,
                "old_unit_price": _round_money(item.price_paid),
                "current_unit_price": _round_money(current_price),
                "old_subtotal": _round_money(previous_line_total),
                "current_subtotal": _round_money(current_line_total),
                "delta": _round_money(current_line_total - previous_line_total),
                "image": product_model.image or item.image,
            })

        existing_cart_item = (
            db.query(Cart)
            .filter(Cart.owner_id == owner_id)
            .filter(Cart.product_id == product_model.id)
            .first()
        )

        if existing_cart_item and merge_duplicates:
            existing_cart_item.quantity = int(existing_cart_item.quantity or 0) + qty
            existing_cart_item.checked = False
            merged_count += 1
        else:
            db.add(Cart(
                product_id=product_model.id,
                quantity=qty,
                owner_id=owner_id,
                checked=False,
            ))
            restored_count += 1

        restored_product_ids.append(product_model.id)

    db.commit()

    return {
        "history_id": shopping_history_id,
        "restored_count": restored_count,
        "merged_count": merged_count,
        "missing_count": len(missing_products),
        "previous_total": _round_money(previous_total),
        "current_total": _round_money(current_total),
        "total_delta": _round_money(current_total - previous_total),
        "price_changes": price_changes,
        "missing": missing_products,
        "restored_product_ids": restored_product_ids,
        "message": "Lista ripristinata nel carrello con i prezzi attuali dei prodotti.",
    }


@router.delete("/{shopping_history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shopping_history(user: user_dependency, db: db_dependency, shopping_history_id: int):
    shopping_history_model = (
        db.query(ShoppingHistory)
        .filter(ShoppingHistory.id == shopping_history_id)
        .filter(ShoppingHistory.user_id == user.get("id"))
        .first()
    )
    if shopping_history_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping History not found")
    db.delete(shopping_history_model)
    db.commit()
