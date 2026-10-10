"""Loading the logged-in user's receipts and items from Supabase.

Every function takes the user's own Supabase client, so Row Level Security
guarantees only their data is returned. Shared by the analytics, insights,
budget and export endpoints.
"""

from typing import Any, Callable

from supabase import Client

from app import analytics

# Supabase returns at most 1000 rows per request, so we page through results.
PAGE_SIZE = 1000

ITEM_COLUMNS = (
    "id, name, quantity, unit_price, total_price, categories(name, icon), "
    # !inner lets us filter items by their receipt's date.
    "receipts!inner(id, store_name, purchase_date)"
)


def fetch_all(build_query: Callable[[], Any]) -> list[dict]:
    """Run a query page by page until all rows are loaded."""
    rows: list[dict] = []
    start = 0
    while True:
        page = build_query().range(start, start + PAGE_SIZE - 1).execute().data
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE


def _month_range(first_month: str, last_month: str) -> tuple[str, str]:
    """ISO dates [start, end) covering first_month through last_month."""
    start = analytics.month_start(first_month).isoformat()
    end = analytics.month_start(analytics.shift_month(last_month, 1)).isoformat()
    return start, end


def receipts_between(db: Client, first_month: str, last_month: str) -> list[dict]:
    """The user's receipts from the start of first_month to the end of last_month."""
    start, end = _month_range(first_month, last_month)
    return fetch_all(
        lambda: db.table("receipts")
        .select("id, store_name, purchase_date, total_amount")
        .gte("purchase_date", start)
        .lt("purchase_date", end)
        .order("id")
    )


def items_between(db: Client, first_month: str, last_month: str) -> list[dict]:
    """The user's receipt items bought from first_month through last_month."""
    start, end = _month_range(first_month, last_month)
    return fetch_all(
        lambda: db.table("receipt_items")
        .select(ITEM_COLUMNS)
        .gte("receipts.purchase_date", start)
        .lt("receipts.purchase_date", end)
        .order("id")
    )


def first_receipt_month(db: Client) -> str | None:
    """Month of the user's oldest receipt ("YYYY-MM"), or None if they have none."""
    rows = db.table("receipts").select("purchase_date").order("purchase_date").limit(1).execute().data
    return analytics.month_of(rows[0]["purchase_date"]) if rows else None


def budgets(db: Client) -> list[dict]:
    """The user's budgets with category name and icon."""
    return (
        db.table("budgets")
        .select("category_id, monthly_limit, categories(name, icon)")
        .order("category_id")
        .execute()
        .data
    )
