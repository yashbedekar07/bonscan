"""CSV export in the format German Excel expects.

- Separator ";" and decimal comma ("2,49"), dates as DD.MM.YYYY.
- UTF-8 with a BOM, so Excel shows umlauts (ä, ö, ü) correctly.
- Text cells that start with =, +, -, @ (or a tab/return) are prefixed with "'"
  so Excel never runs them as formulas ("CSV injection"). Item names come from
  AI-read receipts, so we don't trust them.
"""

import csv
import io
from datetime import date

HEADER = ["Date", "Store", "Item", "Quantity", "Unit price", "Total price", "Category", "Receipt ID"]
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def safe_text(value: str | None) -> str:
    """Neutralise text that Excel would treat as a formula."""
    text = value or ""
    return f"'{text}" if text.startswith(_FORMULA_START) else text


def decimal_comma(value: float | None, decimals: int = 2) -> str:
    """2.5 → "2,50"; None → ""."""
    return "" if value is None else f"{value:.{decimals}f}".replace(".", ",")


def quantity_text(value: float | None) -> str:
    """1.0 → "1", 0.512 → "0,512" (no pointless decimals)."""
    if value is None:
        return ""
    return f"{value:g}".replace(".", ",")


def build_csv(items: list[dict]) -> bytes:
    """items: receipt item rows with categories {name} and receipts {id, store_name, purchase_date}."""
    rows = sorted(items, key=lambda i: (i["receipts"]["purchase_date"], i["receipts"]["id"], i["id"]))

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(HEADER)
    for item in rows:
        receipt = item["receipts"]
        writer.writerow([
            date.fromisoformat(receipt["purchase_date"]).strftime("%d.%m.%Y"),
            safe_text(receipt["store_name"]),
            safe_text(item["name"]),
            quantity_text(item["quantity"]),
            decimal_comma(item["unit_price"]),
            decimal_comma(item["total_price"]),
            safe_text((item.get("categories") or {}).get("name")),
            receipt["id"],
        ])
    return ("﻿" + buffer.getvalue()).encode("utf-8")  # BOM first, for Excel
