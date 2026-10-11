"""Checks for the demo data generator (no login, no database)."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import seed_demo  # noqa: E402

from app import analytics  # noqa: E402
from app.services import forecast, insights  # noqa: E402

TODAY = date(2026, 10, 11)
SCHEMA_CATEGORIES = {"Groceries", "Drugstore & Hygiene", "Household", "Eating Out", "Drinks & Snacks",
                     "Transport", "Clothing", "Electronics", "Deposit (Pfand)", "Other"}


@pytest.fixture(scope="module")
def receipts():
    return seed_demo.generate(TODAY)


def as_rows(receipts):
    return [
        {"name": i.name, "quantity": i.quantity, "unit_price": i.unit_price, "total_price": i.total_price,
         "categories": {"name": i.category}, "receipts": {"id": r.id, "store_name": r.store, "purchase_date": r.day.isoformat()}}
        for r in receipts for i in r.items
    ]


def test_same_data_every_run(receipts):
    again = seed_demo.generate(TODAY)
    assert [(r.id, r.store, r.day, r.total) for r in again] == [(r.id, r.store, r.day, r.total) for r in receipts]


def test_size_and_date_range(receipts):
    assert 45 <= len(receipts) <= 60
    assert receipts[-1].day <= TODAY
    assert (TODAY - receipts[0].day).days >= 100  # about 4 months


def test_totals_equal_item_sums_and_categories_exist(receipts):
    for r in receipts:
        assert r.total == round(sum(i.total_price for i in r.items), 2)
        assert 0 <= r.vat < r.total
    assert {i.category for r in receipts for i in r.items} <= SCHEMA_CATEGORIES
    assert set(seed_demo.BUDGETS) <= SCHEMA_CATEGORIES


def test_all_requested_stores_are_used(receipts):
    stores = {r.store for r in receipts}
    for store in ("REWE", "Lidl", "ALDI SÜD", "Edeka", "dm-drogerie markt", "Rossmann", "Bäckerei Thürmann", "DB",
                  "Pizza & Döner Express"):
        assert store in stores


def test_intended_alerts_appear(receipts):
    items = as_rows(receipts)
    current, first = "2026-10", receipts[0].day.strftime("%Y-%m")
    this_month = analytics.category_totals(items, current)
    history = [analytics.category_totals(items, m) for m in forecast.complete_months(current, first)]

    spikes = insights.category_spikes({k: v for k, v in this_month.items() if v > 0}, history)
    assert [a["numbers"]["category"] for a in spikes] == ["Eating Out"]

    prices = insights.price_increases(items, TODAY)
    assert [(a["numbers"]["item"], a["numbers"]["store"]) for a in prices] == [("Butter 250g", "REWE")]

    percent, status = insights.budget_status(this_month["Eating Out"], seed_demo.BUDGETS["Eating Out"])
    assert percent >= 80 and status in ("warning", "over")


def test_refuses_other_accounts(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["seed_demo.py", "--email", "someone@example.com"])
    with pytest.raises(SystemExit, match="only works with demo@bonscan.app"):
        seed_demo.main()
