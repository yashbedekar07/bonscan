"""Analytics endpoints for the dashboard.

Data is loaded with the logged-in user's Supabase client (app/data.py), so Row
Level Security guarantees each user only ever sees their own receipts. The
maths lives in app/analytics.py.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from supabase import Client

from app import analytics, data
from app.auth import get_user_db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# ?month=YYYY-MM (defaults to the current month). Also used by other routers.
MonthParam = Annotated[
    str | None,
    Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Month as YYYY-MM (default: current month)"),
]


# ---------- Response models (also shown in /docs) ----------


class CategorySpend(BaseModel):
    name: str
    icon: str | None
    amount: float
    percent: float  # share of total category spending in the month


class StoreSpend(BaseModel):
    store: str
    amount: float
    visits: int


class Summary(BaseModel):
    month: str
    total_spent: float
    previous_month_total: float
    change_percent: float | None  # None when the previous month had no spending
    receipt_count: int
    average_per_receipt: float | None
    top_store: StoreSpend | None  # most visits
    biggest_category: CategorySpend | None


class MonthTotal(BaseModel):
    month: str
    total: float
    receipt_count: int


class TopItem(BaseModel):
    name: str
    total_spent: float
    times_bought: int


class TopItems(BaseModel):
    by_spend: list[TopItem]
    by_count: list[TopItem]


class PricePoint(BaseModel):
    date: date
    store: str
    price: float  # per unit or per kg


class PriceHistory(BaseModel):
    query: str
    matched_names: list[str]  # item names that were included, so the user can check
    stores: list[str]
    points: list[PricePoint]


# ---------- Endpoints ----------


@router.get("/summary")
def summary(month: MonthParam = None, db: Client = Depends(get_user_db)) -> Summary:
    """Headline numbers for a month: total, change vs previous month, receipts, average,
    most-visited store and biggest category."""
    month = month or analytics.current_month()
    previous = analytics.shift_month(month, -1)

    receipts = data.receipts_between(db, previous, month)  # both months in one query
    month_receipts = [r for r in receipts if analytics.month_of(r["purchase_date"]) == month]
    previous_receipts = [r for r in receipts if analytics.month_of(r["purchase_date"]) == previous]

    return Summary(
        **analytics.summarize(month, month_receipts, previous_receipts, data.items_between(db, month, month))
    )


@router.get("/by-category")
def by_category(month: MonthParam = None, db: Client = Depends(get_user_db)) -> list[CategorySpend]:
    """Spending per category in a month (amount and % of the month's category total)."""
    month = month or analytics.current_month()
    rows = analytics.spending_by_category(data.items_between(db, month, month))
    return [CategorySpend(**row) for row in rows]


@router.get("/by-store")
def by_store(month: MonthParam = None, db: Client = Depends(get_user_db)) -> list[StoreSpend]:
    """Spending and number of visits per store in a month."""
    month = month or analytics.current_month()
    rows = analytics.spending_by_store(data.receipts_between(db, month, month))
    return [StoreSpend(**row) for row in rows]


@router.get("/monthly-trend")
def monthly_trend(
    months: Annotated[int, Query(ge=1, le=36, description="How many months to include")] = 12,
    db: Client = Depends(get_user_db),
) -> list[MonthTotal]:
    """Total spent per month for the last N months (months without receipts show 0)."""
    last = analytics.current_month()
    first = analytics.shift_month(last, -(months - 1))
    rows = analytics.monthly_trend(data.receipts_between(db, first, last), last, months)
    return [MonthTotal(**row) for row in rows]


@router.get("/top-items")
def top_items(
    month: MonthParam = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    db: Client = Depends(get_user_db),
) -> TopItems:
    """Most-bought items in a month, by money spent and by number of purchases."""
    month = month or analytics.current_month()
    return TopItems(**analytics.top_items(data.items_between(db, month, month), limit))


@router.get("/price-history")
def price_history(
    item: Annotated[str, Query(min_length=2, max_length=100, description="Item to look up, e.g. 'milch'")],
    db: Client = Depends(get_user_db),
) -> PriceHistory:
    """Price over time for one item, per store. Similar names (sizes, weights removed) are grouped."""
    words = analytics.normalize_item_name(item).split()
    if not words:
        raise HTTPException(422, "Please search for an item name with letters, e.g. 'milch'.")

    # Let the database pre-filter on the longest word (letters only, so it's safe in a LIKE pattern);
    # the exact whole-word matching happens in analytics.price_history.
    longest = max(words, key=len)
    rows = data.fetch_all(
        lambda: db.table("receipt_items").select(data.ITEM_COLUMNS).ilike("name", f"%{longest}%").order("id")
    )
    return PriceHistory(**analytics.price_history(rows, item))
