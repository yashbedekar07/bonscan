"""Forecast and alert endpoints. The logic is in app/services/forecast.py and insights.py."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import Client

from app import analytics, data
from app.auth import get_user_db
from app.services import forecast, insights

router = APIRouter(prefix="/api/insights", tags=["insights"])


class CategoryProjection(BaseModel):
    name: str
    icon: str | None
    spent_so_far: float
    projected: float


class ForecastMonth(BaseModel):
    month: str
    total: float
    weight: float


class NextMonthForecast(BaseModel):
    month: str
    forecast: float | None  # None when there isn't enough data
    message: str | None  # explains why there's no forecast
    based_on: list[ForecastMonth]


class Forecast(BaseModel):
    month: str
    today: date
    days_passed: int
    days_in_month: int
    spent_so_far: float
    projected_total: float
    categories: list[CategoryProjection]
    next_month: NextMonthForecast


class Alert(BaseModel):
    type: str  # "warning" or "info"
    kind: str  # "budget", "category_spike" or "price_increase"
    message: str
    numbers: dict[str, Any]  # the figures behind the message


@router.get("/forecast")
def get_forecast(db: Client = Depends(get_user_db)) -> Forecast:
    """End-of-month projection for the current month (total and per category) and a forecast
    for next month based on the last 3 complete months."""
    today = date.today()
    current = analytics.current_month()
    first_month = data.first_receipt_month(db)

    receipts = data.receipts_between(db, analytics.shift_month(current, -3), current)
    totals = {row["month"]: row["total"] for row in analytics.monthly_trend(receipts, current, 4)}
    spent = totals[current]

    categories = analytics.spending_by_category(data.items_between(db, current, current))

    return Forecast(
        month=current,
        today=today,
        days_passed=today.day,
        days_in_month=forecast.days_in_month(current),
        spent_so_far=spent,
        projected_total=forecast.project_month_end(spent, today),
        categories=forecast.project_categories(categories, today),
        next_month=forecast.next_month_forecast(totals, current, first_month),
    )


@router.get("/alerts")
def get_alerts(db: Client = Depends(get_user_db)) -> list[Alert]:
    """Plain-language alerts for the current month: budgets, unusual category spending and
    price increases. Warnings come first."""
    today = date.today()
    current = analytics.current_month()
    first_month = data.first_receipt_month(db)
    if first_month is None:
        return []  # no receipts, nothing to say

    # One query for the last 12 months covers everything below.
    items = data.items_between(db, analytics.shift_month(current, -11), current)
    current_totals = analytics.category_totals(items, current)

    # Category spikes: compare with the previous complete months that have data.
    history_months = forecast.complete_months(current, first_month)
    history = [analytics.category_totals(items, month) for month in history_months]
    spikes = insights.category_spikes({k: v for k, v in current_totals.items() if v > 0}, history)

    # Budgets: spent so far and the end-of-month projection.
    budgets = []
    for row in data.budgets(db):
        name = (row.get("categories") or {}).get("name") or "Unknown"
        spent = max(current_totals.get(name, 0.0), 0.0)
        budgets.append({
            "name": name,
            "limit": row["monthly_limit"],
            "spent": spent,
            "projected": forecast.project_month_end(spent, today),
        })

    alerts = insights.budget_alerts(budgets) + spikes + insights.price_increases(items, today)
    return [Alert(**a) for a in insights.sort_alerts(alerts)]
