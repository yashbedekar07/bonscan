"""Spending forecasts, in plain Python (pandas/numpy are blocked on the dev machine).

Two simple, explainable methods:

1. End-of-month projection (current month)
   Assume you keep spending at the same daily pace as so far this month:

       projected = spent_so_far / days_passed * days_in_month

   "days_passed" includes today. Example: 120 € spent by 10 October (10 of 31 days)
   → 120 / 10 * 31 = 372 €. Early in the month one big shop can swing this a lot,
   so the frontend always shows how many days the projection is based on.

2. Next-month forecast
   A weighted average of the last 3 complete months, where recent months count more:

       forecast = 0.5 * last month + 0.3 * the month before + 0.2 * the one before that

   Months before your first receipt don't count as "0 €": they're missing data.
   If only 2 of the 3 months are available, their weights are rescaled to add up
   to 1 (0.5/0.3 → 0.625/0.375). With fewer than 2 months there's no forecast.
"""

import calendar
from datetime import date

from app.analytics import shift_month

WEIGHTS = (0.5, 0.3, 0.2)  # most recent complete month first
MIN_MONTHS = 2
NOT_ENOUGH_DATA = "Not enough data yet: a forecast needs at least 2 complete months of receipts."


def days_in_month(month: str) -> int:
    year, mon = map(int, month.split("-"))
    return calendar.monthrange(year, mon)[1]


def project_month_end(spent_so_far: float, today: date) -> float:
    """Project the current month's total from the spending pace so far (see module docstring)."""
    days_passed = today.day
    total_days = days_in_month(today.strftime("%Y-%m"))
    return round(spent_so_far / days_passed * total_days, 2)


def project_categories(categories: list[dict], today: date) -> list[dict]:
    """Apply the same projection to each category: [{name, icon, amount}] → adds 'projected'."""
    return [
        {
            "name": c["name"],
            "icon": c.get("icon"),
            "spent_so_far": round(c["amount"], 2),
            "projected": project_month_end(c["amount"], today),
        }
        for c in categories
    ]


def complete_months(current_month: str, first_data_month: str | None, count: int = 3) -> list[str]:
    """The last `count` complete months before current_month that are on/after the first data month.

    Most recent first. Returns [] if the user has no receipts at all.
    """
    if first_data_month is None:
        return []
    months = [shift_month(current_month, -offset) for offset in range(1, count + 1)]
    return [m for m in months if m >= first_data_month]


def next_month_forecast(monthly_totals: dict[str, float], current_month: str, first_data_month: str | None) -> dict:
    """Weighted average of the last 3 complete months (see module docstring).

    monthly_totals maps "YYYY-MM" → total spent; missing months count as 0 €
    as long as they're after the user's first receipt.
    """
    months = complete_months(current_month, first_data_month)
    result = {"month": shift_month(current_month, 1), "forecast": None, "message": None, "based_on": []}

    if len(months) < MIN_MONTHS:
        result["message"] = NOT_ENOUGH_DATA
        return result

    weights = WEIGHTS[: len(months)]
    scale = 1 / sum(weights)  # rescale so the weights add up to 1
    based_on = [
        {"month": m, "total": round(monthly_totals.get(m, 0.0), 2), "weight": round(w * scale, 3)}
        for m, w in zip(months, weights)
    ]
    result["forecast"] = round(sum(row["total"] * row["weight"] for row in based_on), 2)
    result["based_on"] = based_on
    return result
