"""CSV export of the user's receipt items (formatting in app/services/csv_export.py)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from supabase import Client

from app import data
from app.auth import get_user_db
from app.services.csv_export import build_csv

router = APIRouter(prefix="/api/export", tags=["export"])

MAX_DAYS = 366 * 5  # keep exports to a sensible size


@router.get("/csv")
def export_csv(
    from_date: Annotated[date, Query(alias="from", description="First day, YYYY-MM-DD")],
    to_date: Annotated[date, Query(alias="to", description="Last day (included), YYYY-MM-DD")],
    db: Client = Depends(get_user_db),
) -> Response:
    """Download one row per receipt item between two dates, as a CSV for German Excel
    (";" separator, comma decimals)."""
    if from_date > to_date:
        raise HTTPException(422, "'from' must be on or before 'to'.")
    if (to_date - from_date).days > MAX_DAYS:
        raise HTTPException(422, "Please export at most 5 years at a time.")

    start, end = from_date.isoformat(), to_date.isoformat()
    items = data.fetch_all(
        lambda: db.table("receipt_items")
        .select(data.ITEM_COLUMNS)
        .gte("receipts.purchase_date", start)
        .lte("receipts.purchase_date", end)
        .order("id")
    )

    return Response(
        content=build_csv(items),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="bonscan_{start}_{end}.csv"'},
    )
