"""Unit tests for app/services/insights.py (no database, no API calls)."""

from datetime import date

from app.services import insights

TODAY = date(2026, 10, 10)


def item(name, store, day, unit_price, quantity=1):
    """A made-up receipt item row, shaped like the rows loaded from Supabase."""
    return {
        "name": name,
        "quantity": quantity,
        "unit_price": unit_price,
        "total_price": round(unit_price * quantity, 2),
        "receipts": {"store_name": store, "purchase_date": day},
    }


# ---------- Category spikes ----------


def test_clear_spike_is_flagged():
    history = [{"Groceries": 100.0}, {"Groceries": 110.0}, {"Groceries": 90.0}]  # average 100
    alerts = insights.category_spikes({"Groceries": 200.0}, history)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["type"] == "warning"
    assert alert["kind"] == "category_spike"
    assert alert["numbers"] == {"category": "Groceries", "amount": 200.0, "average": 100.0, "months_compared": 3}
    assert "100 % more" in alert["message"]


def test_small_amounts_are_not_flagged_even_with_big_percentage():
    # +50 %, but only 1 € more → noise
    assert insights.category_spikes({"Transport": 3.0}, [{"Transport": 2.0}]) == []


def test_big_amount_but_small_percentage_is_not_flagged():
    # +20 € but only +16.7 %
    assert insights.category_spikes({"Groceries": 140.0}, [{"Groceries": 120.0}]) == []


def test_exactly_30_percent_is_not_flagged():
    # Must be MORE than 30 % higher.
    assert insights.category_spikes({"Groceries": 130.0}, [{"Groceries": 100.0}]) == []


def test_missing_category_in_a_month_counts_as_zero():
    # Average of 60, 0, 0 = 20 → 40 € is +100 % and +20 € → flagged
    history = [{"Household": 60.0}, {}, {}]
    alerts = insights.category_spikes({"Household": 40.0}, history)
    assert [a["numbers"]["average"] for a in alerts] == [20.0]


def test_brand_new_category_is_flagged():
    alerts = insights.category_spikes({"Electronics": 50.0}, [{"Groceries": 100.0}])
    assert len(alerts) == 1
    assert "up from" in alerts[0]["message"]


def test_spikes_with_empty_data():
    assert insights.category_spikes({}, []) == []
    assert insights.category_spikes({}, [{"Groceries": 100.0}]) == []


def test_spikes_with_one_month_only():
    # No previous months to compare with → no alerts, however high the spending.
    assert insights.category_spikes({"Groceries": 500.0}, []) == []


# ---------- Budgets ----------


def test_budget_status_thresholds():
    assert insights.budget_status(79.0, 100.0) == (79.0, "ok")
    assert insights.budget_status(80.0, 100.0) == (80.0, "warning")
    assert insights.budget_status(100.0, 100.0) == (100.0, "warning")
    assert insights.budget_status(100.5, 100.0) == (100.5, "over")


def test_budget_alerts():
    budgets = [
        {"name": "Groceries", "limit": 200.0, "spent": 230.0, "projected": 690.0},  # over
        {"name": "Household", "limit": 50.0, "spent": 42.0, "projected": 130.2},  # 84 %
        {"name": "Drinks & Snacks", "limit": 60.0, "spent": 30.0, "projected": 93.0},  # 50 %, but projected over
        {"name": "Clothing", "limit": 100.0, "spent": 10.0, "projected": 31.0},  # fine
    ]
    alerts = insights.budget_alerts(budgets)

    assert [(a["type"], a["numbers"]["category"]) for a in alerts] == [
        ("warning", "Groceries"),
        ("warning", "Household"),
        ("info", "Drinks & Snacks"),
    ]
    assert "30,00 € over" in alerts[0]["message"]
    assert alerts[1]["numbers"]["percent"] == 84.0
    assert alerts[2]["numbers"]["projected"] == 93.0


def test_budget_alerts_with_empty_data():
    assert insights.budget_alerts([]) == []


# ---------- Price increases ----------


def test_price_increase_same_item_same_store_is_flagged():
    items = [
        item("H-Milch 3,5%", "REWE", "2026-09-01", 1.00),
        item("H-MILCH 3,5% 1L", "Rewe", "2026-10-05", 1.20),  # same item and store, +20 %
    ]
    alerts = insights.price_increases(items, TODAY)

    assert len(alerts) == 1
    numbers = alerts[0]["numbers"]
    assert (numbers["previous_price"], numbers["latest_price"], numbers["percent"]) == (1.0, 1.2, 20)
    assert alerts[0]["type"] == "info"


def test_small_price_increase_is_not_flagged():
    items = [item("Butter", "Lidl", "2026-09-01", 2.00), item("Butter", "Lidl", "2026-10-01", 2.20)]  # +10 %
    assert insights.price_increases(items, TODAY) == []


def test_different_stores_are_not_compared():
    items = [item("Butter", "Lidl", "2026-09-01", 1.50), item("Butter", "REWE", "2026-10-01", 2.50)]
    assert insights.price_increases(items, TODAY) == []


def test_old_price_increases_are_ignored():
    # Latest purchase more than 60 days ago.
    items = [item("Kaffee", "ALDI", "2026-05-01", 4.00), item("Kaffee", "ALDI", "2026-06-01", 6.00)]
    assert insights.price_increases(items, TODAY) == []


def test_only_latest_two_purchases_are_compared():
    # Went up a lot in the past, but the latest change is a price drop → no alert.
    items = [
        item("Käse", "REWE", "2026-08-01", 2.00),
        item("Käse", "REWE", "2026-09-01", 3.00),
        item("Käse", "REWE", "2026-10-01", 2.90),
    ]
    assert insights.price_increases(items, TODAY) == []


def test_weighed_items_use_price_per_kg():
    items = [
        item("Bananen 0,8 kg", "REWE", "2026-09-01", 1.50, quantity=0.8),
        item("Bananen 1,2 kg", "REWE", "2026-10-01", 1.50, quantity=1.2),  # more kilos, same price/kg
    ]
    assert insights.price_increases(items, TODAY) == []


def test_bottle_deposit_is_not_a_price_increase():
    # "Pfand" 0,25 € for one bottle, then 1,50 € for a six-pack: not a price rise.
    items = [item("Pfand", "REWE", "2026-09-01", 0.25), item("Pfand", "REWE", "2026-10-01", 1.50)]
    for row in items:
        row["categories"] = {"name": "Deposit (Pfand)"}
    assert insights.price_increases(items, TODAY) == []


def test_price_increases_with_empty_data():
    assert insights.price_increases([], TODAY) == []


# ---------- Ordering and formatting ----------


def test_warnings_come_first():
    alerts = [{"type": "info", "kind": "x"}, {"type": "warning", "kind": "y"}, {"type": "info", "kind": "z"}]
    assert [a["kind"] for a in insights.sort_alerts(alerts)] == ["y", "x", "z"]


def test_eur_formatting():
    assert insights.eur(1234.5) == "1.234,50 €"
    assert insights.eur(0.3) == "0,30 €"
