"""Receipt extraction with Google Gemini.

Flow:
1. Send the receipt photo + a prompt with German-receipt rules to Gemini.
2. Ask for structured JSON output matching our Pydantic schema, so the
   response is always valid JSON in the shape we expect.
3. Clean up the result (rounding, date check, unknown categories) and collect
   warnings, e.g. when the items don't add up to the total.
"""

import copy
import json
from datetime import date
from functools import lru_cache
from typing import Any

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field, ValidationError

from app.categories import FALLBACK_CATEGORY
from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TIMEOUT_SECONDS, ConfigError

# Max allowed difference (EUR) between the sum of items and the receipt total.
TOTAL_TOLERANCE = 0.05


# ---------- Result schema (sent to Gemini and used to validate its answer) ----------


class ExtractedItem(BaseModel):
    name: str = Field(description="Item name exactly as printed on the receipt.")
    quantity: float = Field(
        default=1, description="Number of units, or weight in kg for weighed items."
    )
    unit_price: float | None = Field(
        default=None, description="Price per unit or per kg in EUR, if shown."
    )
    total_price: float = Field(
        description="Line total in EUR. Negative for discounts and returned deposit."
    )
    suggested_category: str = Field(description="One of the allowed category names.")


class ReceiptExtraction(BaseModel):
    store_name: str | None = Field(default=None, description="Shop chain name, e.g. REWE, Lidl.")
    purchase_date: str | None = Field(default=None, description="Purchase date as YYYY-MM-DD.")
    total_amount: float | None = Field(default=None, description="Total paid in EUR (SUMME).")
    vat_amount: float | None = Field(default=None, description="Sum of all VAT (MwSt) amounts in EUR.")
    currency: str = Field(default="EUR", description="ISO currency code, normally EUR.")
    items: list[ExtractedItem] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    draft: ReceiptExtraction  # cleaned-up result for the review form
    warnings: list[str]  # things the user should double-check
    raw: dict[str, Any]  # Gemini's untouched JSON, stored later in raw_ai_json


class ExtractionError(Exception):
    """Extraction failed; `message` is safe to show to the user."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


# ---------- Prompt ----------

PROMPT_TEMPLATE = """\
You are reading a photo of a German shop receipt (Kassenbon), for example from \
REWE, Lidl, ALDI, EDEKA, Kaufland, Netto, Penny, dm or Rossmann.
Extract the purchase data as JSON that matches the given schema.

Rules:
1. Numbers: German receipts use a comma as the decimal separator. "2,49" means 2.49.
   Return plain numbers (2.49) without currency symbols.
2. Total: total_amount is the amount next to "SUMME", "Summe EUR", "Gesamt", "Zu zahlen" or "Total".
3. VAT: the tax summary (lines like "MwSt", "USt", "Steuer", "A 7% ...", "B 19% ...") is NOT an item.
   vat_amount is the sum of the tax amounts (the MwSt/Steuer column), not the net or gross amounts.
   The letters A/B/1/2 printed after item prices only mark the tax rate; ignore them.
4. Deposit: "Pfand", "Leergut", "Pfandrückgabe" and "Pfandbon" lines are items in the category
   "Deposit (Pfand)". Deposit you get back (Leergut, Pfandbon) has a negative total_price.
5. Discounts: "Rabatt", "Preisvorteil", "Coupon", "Aktion", "Sofortrabatt" and other minus lines are
   separate items with a NEGATIVE total_price. Use the category of the discounted item if it is clear,
   otherwise "Other".
6. Quantities: a line like "2 x 1,29" or "2 Stk x 1,29" belongs to the item next to it:
   quantity 2, unit_price 1.29, total_price 2.58. For weighed items ("0,512 kg x 2,99 EUR/kg")
   quantity is 0.512 and unit_price is 2.99. Otherwise quantity is 1.
7. Ignore everything that is not a purchased item: payment lines (BAR, EC-Karte, Girocard,
   Kreditkarte, Gegeben, Rückgeld), card terminal and TSE blocks, Beleg/Terminal/Trace numbers,
   loyalty points (Payback), store address, opening hours and greetings.
8. Item names: keep the original name as printed. Only if it is a cryptic abbreviation, append a
   short English explanation in brackets, e.g. "GOUDA JG. (young gouda)".
9. suggested_category must be exactly one of: {categories}.
   Use "{fallback}" if nothing fits.
10. purchase_date: German receipts print DD.MM.YYYY or DD.MM.YY. Return it as YYYY-MM-DD.
11. store_name: the shop chain, e.g. "REWE", "Lidl", "ALDI SÜD", "dm-drogerie markt".
12. If a value is unreadable, use null. Never invent items or amounts.
"""


def build_prompt(category_names: list[str]) -> str:
    return PROMPT_TEMPLATE.format(
        categories=", ".join(f'"{name}"' for name in category_names),
        fallback=FALLBACK_CATEGORY,
    )


def build_response_schema(category_names: list[str]) -> dict[str, Any]:
    """JSON schema for Gemini's structured output.

    Same as ReceiptExtraction, but suggested_category is restricted to the
    category names that currently exist in the database.
    """
    schema = copy.deepcopy(ReceiptExtraction.model_json_schema())
    category_property = schema["$defs"]["ExtractedItem"]["properties"]["suggested_category"]
    category_property["enum"] = category_names
    return schema


# ---------- Gemini call ----------


@lru_cache
def get_gemini_client() -> genai.Client:
    """Shared Gemini client. Raises ConfigError if the API key is missing."""
    if not GEMINI_API_KEY:
        raise ConfigError("Gemini is not configured: set GEMINI_API_KEY in backend/.env.")
    return genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_SECONDS * 1000),  # milliseconds
    )


def extract_receipt(image_bytes: bytes, mime_type: str, category_names: list[str]) -> ExtractionResult:
    """Read a receipt image with Gemini. Raises ExtractionError on failure."""
    client = get_gemini_client()

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                build_prompt(category_names),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=build_response_schema(category_names),
                temperature=0,  # we want the same answer every time, not creativity
            ),
        )
    except httpx.TimeoutException:
        raise ExtractionError(504, "The AI took too long to read the receipt. Please try again.")
    except errors.APIError as error:
        raise _friendly_api_error(error)

    # Parse and validate Gemini's JSON against our schema.
    try:
        raw = json.loads(response.text or "")
        draft = ReceiptExtraction.model_validate(raw)
    except (json.JSONDecodeError, ValidationError):
        raise ExtractionError(
            422, "Couldn't read this receipt. Try a sharper, well-lit photo of the whole receipt."
        )

    warnings = clean_up(draft, category_names)
    return ExtractionResult(draft=draft, warnings=warnings, raw=raw)


def _friendly_api_error(error: errors.APIError) -> ExtractionError:
    """Turn a Gemini API error into a message the user can act on."""
    if error.code == 429:
        return ExtractionError(
            429, "The AI is busy (free tier limit reached). Please wait a minute and try again."
        )
    if error.code in (401, 403):
        return ExtractionError(500, "The Gemini API key is invalid or not allowed to use this model.")
    if error.code == 404:
        return ExtractionError(500, f"Gemini model '{GEMINI_MODEL}' not found. Check GEMINI_MODEL in backend/.env.")
    if error.code == 400:
        return ExtractionError(400, "The AI couldn't process this image. Please try a different photo.")
    if error.code == 504:
        return ExtractionError(504, "The AI took too long to read the receipt. Please try again.")
    return ExtractionError(502, "The AI service is unavailable right now. Please try again later.")


# ---------- Clean-up and validation ----------


def clean_up(draft: ReceiptExtraction, category_names: list[str]) -> list[str]:
    """Normalise the draft in place and return a list of warnings for the user."""
    warnings: list[str] = []

    # Round money to cents (AI output can contain values like 2.4899999).
    draft.total_amount = _round_money(draft.total_amount)
    draft.vat_amount = _round_money(draft.vat_amount)
    draft.currency = (draft.currency or "EUR").upper()

    # Dates must be valid YYYY-MM-DD; otherwise let the user fill it in.
    if draft.purchase_date:
        try:
            date.fromisoformat(draft.purchase_date)
        except ValueError:
            warnings.append(f"Couldn't understand the date '{draft.purchase_date}'. Please enter it.")
            draft.purchase_date = None
    else:
        warnings.append("No purchase date found. Please enter it.")

    if not draft.store_name:
        warnings.append("No store name found. Please enter it.")

    for item in draft.items:
        item.total_price = round(item.total_price, 2)
        item.unit_price = _round_money(item.unit_price)
        if item.suggested_category not in category_names:
            item.suggested_category = FALLBACK_CATEGORY

    if not draft.items:
        warnings.append("No items found on the receipt.")

    # The key sanity check: do the items add up to the total?
    if draft.total_amount is None:
        warnings.append("No total amount found. Please enter it.")
    else:
        items_sum = round(sum(item.total_price for item in draft.items), 2)
        if abs(items_sum - draft.total_amount) > TOTAL_TOLERANCE:
            warnings.append(
                f"The items add up to {items_sum:.2f} {draft.currency}, but the receipt total is "
                f"{draft.total_amount:.2f} {draft.currency}. Please check the items."
            )

    return warnings


def _round_money(value: float | None) -> float | None:
    return None if value is None else round(value, 2)
