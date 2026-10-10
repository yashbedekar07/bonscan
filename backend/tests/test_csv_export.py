"""Unit tests for app/services/csv_export.py."""

from app.services.csv_export import build_csv


def row(item_id, name, total, day, receipt="r1", quantity=1, unit=None, category="Groceries", store="REWE"):
    return {
        "id": item_id,
        "name": name,
        "quantity": quantity,
        "unit_price": unit,
        "total_price": total,
        "categories": {"name": category} if category else None,
        "receipts": {"id": receipt, "store_name": store, "purchase_date": day},
    }


def lines(items):
    text = build_csv(items).decode("utf-8")
    assert text.startswith("﻿")  # BOM so Excel detects UTF-8
    return text.lstrip("﻿").split("\r\n")[:-1]


def test_german_excel_format():
    out = lines([row(1, "Bananen", 1.37, "2026-10-08", quantity=0.812, unit=1.69)])
    assert out[0] == "Date;Store;Item;Quantity;Unit price;Total price;Category;Receipt ID"
    assert out[1] == "08.10.2026;REWE;Bananen;0,812;1,69;1,37;Groceries;r1"


def test_rows_sorted_by_date_and_umlauts_kept():
    out = lines([row(2, "Käse", 2.5, "2026-10-09"), row(1, "Äpfel", 1.0, "2026-10-01")])
    assert [line.split(";")[2] for line in out[1:]] == ["Äpfel", "Käse"]


def test_formulas_are_neutralised_but_negative_numbers_stay_numbers():
    out = lines([row(1, "=HYPERLINK(\"x\")", -0.30, "2026-10-01", category=None)])
    fields = out[1].split(";")
    assert fields[2].startswith("\"'=HYPERLINK")  # text prefixed with ' (csv quotes it because of the ")
    assert fields[5] == "-0,30"  # numbers are not escaped
    assert fields[6] == ""  # missing category


def test_empty_export_has_only_header():
    assert len(lines([])) == 1
