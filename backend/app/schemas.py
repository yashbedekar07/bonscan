"""Pydantic models for API requests and responses (also shown in /docs)."""

from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.extraction import ReceiptExtraction


class Category(BaseModel):
    id: int
    name: str
    icon: str | None


# ---------- POST /api/receipts/extract ----------


class ExtractResponse(BaseModel):
    draft: ReceiptExtraction  # AI result for the user to review
    warnings: list[str]
    image_path: str  # where the photo is stored in the "receipts" bucket
    image_url: str  # short-lived signed URL to show the photo
    raw_ai_json: dict[str, Any]  # send this back unchanged when saving


# ---------- POST /api/receipts ----------


class ReceiptItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: float = Field(default=1, gt=0, le=10_000)
    unit_price: float | None = Field(default=None, ge=-10_000, le=10_000)
    total_price: float = Field(ge=-10_000, le=10_000)  # negative for discounts / deposit returns
    category: str = Field(min_length=1)  # category name, e.g. "Groceries"


class ReceiptIn(BaseModel):
    store_name: str = Field(min_length=1, max_length=100)
    purchase_date: date
    total_amount: float = Field(ge=-10_000, le=100_000)
    vat_amount: float | None = Field(default=None, ge=0, le=100_000)
    currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")
    image_path: str | None = None
    raw_ai_json: dict[str, Any] | None = None
    items: list[ReceiptItemIn] = Field(min_length=1, max_length=500)

    @field_validator("store_name")
    @classmethod
    def strip_store_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Store name can't be empty")
        return value

    @field_validator("purchase_date")
    @classmethod
    def not_in_future(cls, value: date) -> date:
        # One day of slack for time zones.
        if value > date.today() + timedelta(days=1):
            raise ValueError("Purchase date can't be in the future")
        return value


class ReceiptCreated(BaseModel):
    id: UUID


# ---------- GET /api/receipts and /api/receipts/{id} ----------


class ReceiptSummary(BaseModel):
    id: UUID
    store_name: str | None
    purchase_date: date | None
    total_amount: float | None
    currency: str
    item_count: int
    created_at: datetime


class ReceiptItemOut(BaseModel):
    id: int
    name: str
    quantity: float
    unit_price: float | None
    total_price: float
    category_id: int | None
    category_name: str | None
    category_icon: str | None


class ReceiptDetail(BaseModel):
    id: UUID
    store_name: str | None
    purchase_date: date | None
    total_amount: float | None
    vat_amount: float | None
    currency: str
    created_at: datetime
    image_url: str | None  # short-lived signed URL, None if no image
    items: list[ReceiptItemOut]
