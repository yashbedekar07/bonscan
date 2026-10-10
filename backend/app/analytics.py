"""Spending calculations for the dashboard, in plain Python.

These functions only do maths on lists of rows (dicts) that the router loads
from Supabase, so they're easy to test without a database.

Conventions:
- Money is rounded to cents at the end of every calculation.
- Months are strings "YYYY-MM".
- Receipt totals (what you paid) are used for overall, store and trend numbers;
  item prices are used for category and item numbers. The two can differ by a
  few cents (rounding, items the AI missed).
"""

import re
from collections import Counter, defaultdict
from datetime import date
from typing import Any

Row = dict[str, Any]

# Items in this category (bottle deposit) are left out of "top items".
DEPOSIT_CATEGORY = "Deposit (Pfand)"
UNCATEGORISED = "Uncategorised"


# ---------- Months ----------


def current_month() -> str:
    return date.today().strftime("%Y-%m")


def shift_month(month: str, delta: int) -> str:
    """shift_month("2026-01", -1) → "2025-12"."""
    year, mon = map(int, month.split("-"))
    index = year * 12 + (mon - 1) + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def month_start(month: str) -> date:
    year, mon = map(int, month.split("-"))
    return date(year, mon, 1)


def month_of(iso_date: str) -> str:
    """"2026-10-08" → "2026-10"."""
    return iso_date[:7]


def _money(value: float) -> float:
    return round(value + 0.0, 2)  # + 0.0 turns -0.0 into 0.0


# ---------- Name normalisation ----------

# A number with an optional size/weight unit, e.g. "500g", "1,5 l", "3,5%", "6x0,5l", "2 Stk".
_SIZE_PATTERN = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:x\s*\d+(?:[.,]\d+)?\s*)?"
    r"(?:kg|g|gr|mg|ml|cl|l|ltr|liter|stk|st|stück|pck|pack|er|%)?(?![a-zäöüß])"
)


def normalize_item_name(name: str) -> str:
    """Make similar item names comparable.

    "H-Milch 3,5% 1L" → "h milch", "GOUDA JG. (young gouda)" → "gouda jg",
    "Bananen 0,812 kg" → "bananen".
    """
    text = name.lower()
    text = re.sub(r"\(.*?\)", " ", text)  # our added English explanations
    text = _SIZE_PATTERN.sub(" ", text)  # sizes, weights, counts, percentages
    text = re.sub(r"[^a-zäöüß]+", " ", text)  # punctuation and leftover digits
    return " ".join(text.split())


def store_key(name: str | None) -> str:
    """Group "REWE", "Rewe" and " REWE  " together."""
    return " ".join((name or "Unknown store").split()).casefold()


def _most_common(names: list[str]) -> str:
    """The spelling that appears most often (first one wins a tie)."""
    return Counter(names).most_common(1)[0][0]


# ---------- Item rows helpers ----------


def _category(item: Row) -> tuple[str, str | None]:
    category = item.get("categories") or {}
    return category.get("name") or UNCATEGORISED, category.get("icon")


def _unit_price(item: Row) -> float | None:
    """Price per unit (or per kg), worked out from the line total if needed."""
    if item.get("unit_price") is not None and item["unit_price"] > 0:
        return float(item["unit_price"])
    quantity = item.get("quantity") or 0
    if quantity > 0 and item["total_price"] > 0:
        return float(item["total_price"]) / quantity
    return None


# ---------- Calculations ----------


def spending_by_category(items: list[Row]) -> list[Row]:
    """Spending per category, biggest first.

    Discounts and returned deposit are negative, so they reduce their category.
    Categories that end up at 0 or below are left out, and percentages are
    relative to the sum of the remaining (positive) categories.
    """
    amounts: dict[str, float] = defaultdict(float)
    icons: dict[str, str | None] = {}
    for item in items:
        name, icon = _category(item)
        amounts[name] += item["total_price"]
        icons[name] = icon

    positive = {name: amount for name, amount in amounts.items() if round(amount, 2) > 0}
    total = sum(positive.values())
    rows = [
        {
            "name": name,
            "icon": icons[name],
            "amount": _money(amount),
            "percent": round(amount / total * 100, 1),
        }
        for name, amount in positive.items()
    ]
    return sorted(rows, key=lambda row: row["amount"], reverse=True)


def spending_by_store(receipts: list[Row]) -> list[Row]:
    """Total spent and number of visits (receipts) per store, biggest spend first."""
    groups: dict[str, list[Row]] = defaultdict(list)
    for receipt in receipts:
        groups[store_key(receipt["store_name"])].append(receipt)

    rows = [
        {
            "store": _most_common([r["store_name"] or "Unknown store" for r in group]),
            "amount": _money(sum(r["total_amount"] or 0 for r in group)),
            "visits": len(group),
        }
        for group in groups.values()
    ]
    return sorted(rows, key=lambda row: (row["amount"], row["visits"]), reverse=True)


def summarize(month: str, month_receipts: list[Row], previous_receipts: list[Row], month_items: list[Row]) -> Row:
    """Headline numbers for one month."""
    total = _money(sum(r["total_amount"] or 0 for r in month_receipts))
    previous_total = _money(sum(r["total_amount"] or 0 for r in previous_receipts))
    count = len(month_receipts)

    # Most-visited store: most receipts, then highest spend.
    stores = spending_by_store(month_receipts)
    top_store = max(stores, key=lambda row: (row["visits"], row["amount"])) if stores else None

    categories = spending_by_category(month_items)

    return {
        "month": month,
        "total_spent": total,
        "previous_month_total": previous_total,
        # No percentage when last month was 0 (division by zero / "infinite" growth).
        "change_percent": round((total - previous_total) / previous_total * 100, 1) if previous_total > 0 else None,
        "receipt_count": count,
        "average_per_receipt": _money(total / count) if count else None,
        "top_store": top_store,
        "biggest_category": categories[0] if categories else None,
    }


def monthly_trend(receipts: list[Row], last_month: str, months: int) -> list[Row]:
    """Total per month for `months` months ending with `last_month`, including empty months."""
    wanted = [shift_month(last_month, -offset) for offset in range(months - 1, -1, -1)]
    totals = {month: 0.0 for month in wanted}
    counts = {month: 0 for month in wanted}
    for receipt in receipts:
        month = month_of(receipt["purchase_date"])
        if month in totals:
            totals[month] += receipt["total_amount"] or 0
            counts[month] += 1
    return [{"month": m, "total": _money(totals[m]), "receipt_count": counts[m]} for m in wanted]


def top_items(items: list[Row], limit: int) -> Row:
    """Most-bought items by money spent and by number of purchases.

    Similar names are grouped (see normalize_item_name). Discounts, deposit
    returns and bottle deposit are left out: they aren't things you "bought".
    """
    groups: dict[str, list[Row]] = defaultdict(list)
    for item in items:
        if item["total_price"] <= 0 or _category(item)[0] == DEPOSIT_CATEGORY:
            continue
        key = normalize_item_name(item["name"]) or item["name"].strip().lower()
        groups[key].append(item)

    rows = [
        {
            "name": _most_common([i["name"] for i in group]),
            "total_spent": _money(sum(i["total_price"] for i in group)),
            "times_bought": len(group),  # number of receipt lines, not kilos
        }
        for group in groups.values()
    ]
    by_spend = sorted(rows, key=lambda r: (r["total_spent"], r["times_bought"]), reverse=True)
    by_count = sorted(rows, key=lambda r: (r["times_bought"], r["total_spent"]), reverse=True)
    return {"by_spend": by_spend[:limit], "by_count": by_count[:limit]}


def price_history(items: list[Row], query: str) -> Row:
    """Price over time for one item, per store.

    An item matches when every word of the (normalised) search appears as a
    whole word in its normalised name: "milch" matches "H-Milch 3,5%" but not
    "Vollmilch" or "Milchschokolade". If a store has several prices on the
    same day, they are averaged.
    """
    query_words = normalize_item_name(query).split()
    matched_names: set[str] = set()
    prices: dict[tuple[str, str], list[float]] = defaultdict(list)  # (date, store key) → prices
    store_names: dict[str, list[str]] = defaultdict(list)

    for item in items:
        name_words = set(normalize_item_name(item["name"]).split())
        if not query_words or not all(word in name_words for word in query_words):
            continue
        price = _unit_price(item)
        if price is None:
            continue
        receipt = item["receipts"]
        key = store_key(receipt["store_name"])
        prices[(receipt["purchase_date"], key)].append(price)
        store_names[key].append(receipt["store_name"] or "Unknown store")
        matched_names.add(item["name"])

    display = {key: _most_common(names) for key, names in store_names.items()}
    points = [
        {"date": day, "store": display[key], "price": _money(sum(values) / len(values))}
        for (day, key), values in sorted(prices.items())
    ]
    # Stores with the most data points first.
    stores = [display[key] for key, _ in Counter(k for (_, k) in prices).most_common()]

    return {
        "query": query,
        "matched_names": sorted(matched_names),
        "stores": stores,
        "points": points,
    }
