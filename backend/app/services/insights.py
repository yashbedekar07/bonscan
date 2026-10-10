"""Spending alerts: plain-language messages about things worth a look.

Three kinds of alert:

1. Category spike: this month's spending in a category is more than 30 % above
   its average over the previous 3 complete months AND at least 10 € more.
   The 10 € rule avoids noise like "Transport went from 2 € to 3 € (+50 %)".
   Months before the first receipt are missing data, not 0 €, so they're skipped.
2. Budget: a budget is already 80 % used (or over), or the end-of-month
   projection says it will go over.
3. Price increase: the same item at the same store now costs more than 15 %
   more than the previous time you bought it (latest purchase in the last
   60 days, at least 5 cents more).

Each alert has a type ("warning" or "info"), a kind, a message and the numbers
behind it, so the user can check the maths.
"""

from collections import defaultdict
from datetime import date, timedelta

from app.analytics import normalize_item_name, store_key

SPIKE_RATIO = 1.30  # more than 30 % above average
SPIKE_MIN_EUR = 10.0  # ... and at least 10 € more
BUDGET_WARN_RATIO = 0.80
PRICE_RISE_RATIO = 1.15  # more than 15 % higher
PRICE_MIN_RISE_EUR = 0.05
PRICE_LOOKBACK_DAYS = 60


def eur(amount: float) -> str:
    """12.5 → "12,50 €" (German format, for messages)."""
    text = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} €"


def _alert(type_: str, kind: str, message: str, **numbers) -> dict:
    return {"type": type_, "kind": kind, "message": message, "numbers": numbers}


# ---------- Budgets ----------


def budget_status(spent: float, limit: float) -> tuple[float, str]:
    """(% used, "ok" | "warning" | "over"): green under 80 %, orange 80–100 %, red over 100 %."""
    percent = round(spent / limit * 100, 1) if limit > 0 else 0.0
    if percent > 100:
        return percent, "over"
    if percent >= BUDGET_WARN_RATIO * 100:
        return percent, "warning"
    return percent, "ok"


def budget_alerts(budgets: list[dict]) -> list[dict]:
    """budgets: [{name, limit, spent, projected (or None)}] for the current month."""
    alerts = []
    for b in budgets:
        percent, status = budget_status(b["spent"], b["limit"])
        numbers = {"category": b["name"], "spent": b["spent"], "limit": b["limit"], "percent": percent}
        if status == "over":
            alerts.append(_alert(
                "warning", "budget",
                f"You're over your {b['name']} budget: {eur(b['spent'])} of {eur(b['limit'])} "
                f"({eur(b['spent'] - b['limit'])} over).",
                **numbers,
            ))
        elif status == "warning":
            alerts.append(_alert(
                "warning", "budget",
                f"You've used {percent:.0f} % of your {b['name']} budget ({eur(b['spent'])} of {eur(b['limit'])}).",
                **numbers,
            ))
        elif b.get("projected") is not None and b["projected"] > b["limit"]:
            alerts.append(_alert(
                "info", "budget",
                f"At this pace you'll spend about {eur(b['projected'])} on {b['name']} this month, "
                f"{eur(b['projected'] - b['limit'])} over your budget of {eur(b['limit'])}.",
                **numbers, projected=b["projected"],
            ))
    return alerts


# ---------- Category spikes ----------


def category_spikes(current: dict[str, float], history: list[dict[str, float]]) -> list[dict]:
    """current: {category: amount} this month; history: one such dict per previous month.

    `history` should only contain months that have data (see complete_months in
    forecast.py). With no history there's nothing to compare against.
    """
    if not history:
        return []

    alerts = []
    for category, amount in sorted(current.items()):
        average = sum(month.get(category, 0.0) for month in history) / len(history)
        if amount > average * SPIKE_RATIO and amount - average >= SPIKE_MIN_EUR:
            increase = round((amount - average) / average * 100) if average > 0 else None
            detail = f"{increase} % more than" if increase is not None else "up from"
            alerts.append(_alert(
                "warning", "category_spike",
                f"{category}: {eur(amount)} this month, {detail} your usual {eur(average)} "
                f"(average of the last {len(history)} months).",
                category=category, amount=round(amount, 2), average=round(average, 2),
                months_compared=len(history),
            ))
    return alerts


# ---------- Price increases ----------


def _unit_price(item: dict) -> float | None:
    if item.get("unit_price") is not None and item["unit_price"] > 0:
        return float(item["unit_price"])
    quantity = item.get("quantity") or 0
    if quantity > 0 and item["total_price"] > 0:
        return float(item["total_price"]) / quantity
    return None


def price_increases(items: list[dict], today: date) -> list[dict]:
    """Compare each item's latest price at a store with the previous time it was bought there.

    items: receipt item rows with name, quantity, unit_price, total_price and
    receipts {store_name, purchase_date}. Several purchases on one day are averaged.
    """
    # (item key, store key) → {date: [prices]}
    history: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    labels: dict[tuple[str, str], tuple[str, str]] = {}

    for item in items:
        price = _unit_price(item)
        key_name = normalize_item_name(item["name"])
        if price is None or not key_name:
            continue
        receipt = item["receipts"]
        key = (key_name, store_key(receipt["store_name"]))
        history[key][receipt["purchase_date"]].append(price)
        labels[key] = (item["name"], receipt["store_name"] or "Unknown store")

    cutoff = (today - timedelta(days=PRICE_LOOKBACK_DAYS)).isoformat()
    alerts = []
    for key, by_date in history.items():
        if len(by_date) < 2:
            continue
        (prev_date, prev_prices), (last_date, last_prices) = sorted(by_date.items())[-2:]
        previous = sum(prev_prices) / len(prev_prices)
        latest = sum(last_prices) / len(last_prices)
        if last_date < cutoff:
            continue
        if latest > previous * PRICE_RISE_RATIO and latest - previous >= PRICE_MIN_RISE_EUR:
            name, store = labels[key]
            increase = round((latest - previous) / previous * 100)
            alerts.append(_alert(
                "info", "price_increase",
                f"{name} at {store} went up {increase} %: {eur(previous)} → {eur(latest)}.",
                item=name, store=store, previous_price=round(previous, 2), latest_price=round(latest, 2),
                previous_date=prev_date, latest_date=last_date, percent=increase,
            ))
    return sorted(alerts, key=lambda a: a["numbers"]["percent"], reverse=True)


def sort_alerts(alerts: list[dict]) -> list[dict]:
    """Warnings first, keeping each group's order."""
    return sorted(alerts, key=lambda a: a["type"] != "warning")
