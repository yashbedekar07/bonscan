"""Unit tests for app/services/forecast.py (no database, no API calls)."""

from datetime import date

import pytest

from app.services import forecast

# Made-up monthly totals: "YYYY-MM" → € spent
TOTALS = {"2026-07": 100.0, "2026-08": 200.0, "2026-09": 300.0, "2026-10": 120.0}


# ---------- End-of-month projection ----------


def test_projection_normal_case():
    # 120 € after 10 of October's 31 days → 120 / 10 * 31
    assert forecast.project_month_end(120.0, date(2026, 10, 10)) == 372.0


def test_projection_on_last_day_equals_spending():
    assert forecast.project_month_end(250.0, date(2026, 10, 31)) == 250.0


def test_projection_handles_february_and_leap_years():
    assert forecast.project_month_end(28.0, date(2027, 2, 14)) == 56.0  # 28 days
    assert forecast.project_month_end(29.0, date(2028, 2, 1)) == 29.0 * 29  # leap year, 29 days


def test_projection_with_no_spending_is_zero():
    assert forecast.project_month_end(0.0, date(2026, 10, 5)) == 0.0


def test_category_projection():
    rows = forecast.project_categories([{"name": "Groceries", "icon": "🛒", "amount": 50.0}], date(2026, 10, 10))
    assert rows == [{"name": "Groceries", "icon": "🛒", "spent_so_far": 50.0, "projected": 155.0}]


# ---------- Next-month forecast ----------


def test_next_month_normal_case():
    result = forecast.next_month_forecast(TOTALS, "2026-10", first_data_month="2026-01")
    # 0.5 * Sep + 0.3 * Aug + 0.2 * Jul = 150 + 60 + 20
    assert result["forecast"] == 230.0
    assert result["month"] == "2026-11"
    assert [row["month"] for row in result["based_on"]] == ["2026-09", "2026-08", "2026-07"]
    assert [row["weight"] for row in result["based_on"]] == [0.5, 0.3, 0.2]
    assert result["message"] is None


def test_next_month_ignores_current_incomplete_month():
    # Changing October (the current month) must not change the forecast.
    changed = {**TOTALS, "2026-10": 9999.0}
    assert forecast.next_month_forecast(changed, "2026-10", "2026-01")["forecast"] == 230.0


def test_next_month_with_empty_data():
    result = forecast.next_month_forecast({}, "2026-10", first_data_month=None)
    assert result["forecast"] is None
    assert result["message"] == forecast.NOT_ENOUGH_DATA
    assert result["based_on"] == []


def test_next_month_with_one_month_only():
    # First receipt in September → only one complete month (September) → no forecast.
    result = forecast.next_month_forecast({"2026-09": 300.0, "2026-10": 50.0}, "2026-10", "2026-09")
    assert result["forecast"] is None
    assert result["message"] == forecast.NOT_ENOUGH_DATA


def test_next_month_with_two_months_rescales_weights():
    # Only Sep and Aug available: 0.5/0.3 become 0.625/0.375.
    result = forecast.next_month_forecast(TOTALS, "2026-10", first_data_month="2026-08")
    assert [row["weight"] for row in result["based_on"]] == [0.625, 0.375]
    assert result["forecast"] == pytest.approx(300 * 0.625 + 200 * 0.375)  # 262.5


def test_months_without_receipts_after_first_receipt_count_as_zero():
    # First receipt in July, nothing in Aug/Sep → those months really were 0 €.
    result = forecast.next_month_forecast({"2026-07": 100.0}, "2026-10", "2026-07")
    assert result["forecast"] == 20.0  # 0.5*0 + 0.3*0 + 0.2*100


def test_forecast_across_new_year():
    totals = {"2025-12": 400.0, "2025-11": 300.0, "2025-10": 200.0}
    result = forecast.next_month_forecast(totals, "2026-01", "2025-01")
    assert result["month"] == "2026-02"
    assert result["forecast"] == 330.0  # 200 + 90 + 40
