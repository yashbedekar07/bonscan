"""Receipt endpoints: scan with AI, save, list, view and delete.

All endpoints are protected. Database and storage calls use a Supabase client
that acts as the logged-in user (`db`), so Row Level Security and the storage
policies in supabase/schema.sql decide what each user can access. We still
filter by user_id where it makes queries clearer, but security doesn't rely on it.
"""

import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from postgrest.exceptions import APIError
from supabase import Client

from app.auth import CurrentUser, get_current_user, get_user_db
from app.categories import category_ids_by_name
from app.config import RECEIPTS_BUCKET, SCAN_LIMIT_PER_DAY, ConfigError
from app.extraction import ExtractionError, extract_receipt, get_gemini_client
from app.images import MAX_IMAGE_BYTES, ImageError, prepare_image
from app.schemas import (
    ExtractResponse,
    ReceiptCreated,
    ReceiptDetail,
    ReceiptIn,
    ReceiptItemOut,
    ReceiptSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/receipts", tags=["receipts"])

# How long signed image URLs stay valid.
SIGNED_URL_SECONDS = 10 * 60


def _signed_url(db: Client, image_path: str) -> str | None:
    try:
        return db.storage.from_(RECEIPTS_BUCKET).create_signed_url(image_path, SIGNED_URL_SECONDS)["signedUrl"]
    except Exception:
        logger.exception("Could not sign image URL for %s", image_path)
        return None


def _register_scan(db: Client) -> None:
    """Count one AI scan for the user, or raise 429 if today's limit is reached.

    The counting happens in the database function register_scan (supabase/schema.sql),
    which users can't bypass by writing to the table themselves.
    """
    try:
        rows = db.rpc("register_scan", {"daily_limit": SCAN_LIMIT_PER_DAY}).execute().data
    except APIError as error:
        if error.code == "PGRST202":  # function doesn't exist
            raise ConfigError("Scan limit not set up: run supabase/schema.sql again in the Supabase SQL Editor.")
        raise
    row = rows[0] if isinstance(rows, list) else rows
    if not row["allowed"]:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Daily scan limit reached ({SCAN_LIMIT_PER_DAY} scans per day). Try again tomorrow.",
        )


@router.post("/extract")
def extract(
    file: UploadFile = File(..., description="Receipt photo (JPG, PNG or WEBP, max 10 MB)"),
    user: CurrentUser = Depends(get_current_user),
    db: Client = Depends(get_user_db),
) -> ExtractResponse:
    """Upload a receipt photo and let the AI read it. Nothing is saved to the database yet."""
    get_gemini_client()  # fail early (503) if Gemini isn't configured, before uploading anything

    # Read at most 1 byte more than allowed, so we can detect files that are too big.
    data = file.file.read(MAX_IMAGE_BYTES + 1)
    try:
        image = prepare_image(data)
    except ImageError as error:
        raise HTTPException(error.status_code, error.message)

    # Fair use of our Gemini quota: count this scan, or stop here if the daily limit is reached.
    # (Invalid files above don't count; every scan that reaches the AI does.)
    _register_scan(db)

    # Store the photo in the user's own folder: <user_id>/<uuid>.<ext>
    # (the storage policy only allows uploads into the user's own folder).
    bucket = db.storage.from_(RECEIPTS_BUCKET)
    image_path = f"{user.id}/{uuid4()}.{image.extension}"
    try:
        bucket.upload(image_path, image.data, {"content-type": image.mime_type})
    except Exception:
        logger.exception("Upload to storage failed")
        raise HTTPException(502, "Couldn't store the image. Please try again.")

    try:
        result = extract_receipt(image.data, image.mime_type, list(category_ids_by_name(db)))
    except ExtractionError as error:
        bucket.remove([image_path])  # don't keep photos we couldn't use
        raise HTTPException(error.status_code, error.message)

    return ExtractResponse(
        draft=result.draft,
        warnings=result.warnings,
        image_path=image_path,
        image_url=_signed_url(db, image_path) or "",
        raw_ai_json=result.raw,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_receipt(
    receipt: ReceiptIn,
    user: CurrentUser = Depends(get_current_user),
    db: Client = Depends(get_user_db),
) -> ReceiptCreated:
    """Save a reviewed receipt and its items."""
    # Users may only attach images from their own folder.
    if receipt.image_path and not receipt.image_path.startswith(f"{user.id}/"):
        raise HTTPException(400, "Invalid image path.")

    # Map category names to ids and reject unknown ones.
    category_ids = category_ids_by_name(db)
    unknown = sorted({item.category for item in receipt.items} - category_ids.keys())
    if unknown:
        raise HTTPException(422, f"Unknown categories: {', '.join(unknown)}")

    receipt_row = (
        db.table("receipts")
        .insert(
            {
                "user_id": user.id,
                "store_name": receipt.store_name,
                "purchase_date": receipt.purchase_date.isoformat(),
                "total_amount": round(receipt.total_amount, 2),
                "vat_amount": None if receipt.vat_amount is None else round(receipt.vat_amount, 2),
                "currency": receipt.currency,
                "image_path": receipt.image_path,
                "raw_ai_json": receipt.raw_ai_json,
            }
        )
        .execute()
        .data[0]
    )

    items = [
        {
            "receipt_id": receipt_row["id"],
            "name": item.name.strip(),
            "quantity": item.quantity,
            "unit_price": None if item.unit_price is None else round(item.unit_price, 2),
            "total_price": round(item.total_price, 2),
            "category_id": category_ids[item.category],
        }
        for item in receipt.items
    ]
    try:
        db.table("receipt_items").insert(items).execute()
    except Exception:
        # No transactions over the REST API, so undo the receipt by hand.
        logger.exception("Saving receipt items failed")
        db.table("receipts").delete().eq("id", receipt_row["id"]).execute()
        raise HTTPException(500, "Couldn't save the receipt items. Please try again.")

    return ReceiptCreated(id=receipt_row["id"])


@router.get("")
def list_receipts(
    user: CurrentUser = Depends(get_current_user),
    db: Client = Depends(get_user_db),
) -> list[ReceiptSummary]:
    """List the user's receipts, newest purchase first."""
    rows = (
        db.table("receipts")
        # receipt_items(count) asks Supabase to count the related items for us.
        .select("id, store_name, purchase_date, total_amount, currency, created_at, receipt_items(count)")
        .eq("user_id", user.id)
        .order("purchase_date", desc=True)
        .order("created_at", desc=True)
        .execute()
        .data
    )
    summaries = []
    for row in rows:
        # Supabase returns the count as [{"count": 5}].
        counts = row.pop("receipt_items")
        summaries.append(ReceiptSummary(**row, item_count=counts[0]["count"] if counts else 0))
    return summaries


def _get_receipt(db: Client, receipt_id: UUID, columns: str) -> dict:
    """Fetch one receipt (RLS only returns the user's own), or raise 404."""
    rows = db.table("receipts").select(columns).eq("id", str(receipt_id)).limit(1).execute().data
    if not rows:
        raise HTTPException(404, "Receipt not found.")
    return rows[0]


@router.get("/{receipt_id}")
def get_receipt(receipt_id: UUID, db: Client = Depends(get_user_db)) -> ReceiptDetail:
    """One receipt with its items and a short-lived link to the photo."""
    row = _get_receipt(
        db,
        receipt_id,
        "id, store_name, purchase_date, total_amount, vat_amount, currency, image_path, created_at, "
        "receipt_items(id, name, quantity, unit_price, total_price, category_id, categories(name, icon))",
    )

    items = [
        ReceiptItemOut(
            id=item["id"],
            name=item["name"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            total_price=item["total_price"],
            category_id=item["category_id"],
            category_name=(item["categories"] or {}).get("name"),
            category_icon=(item["categories"] or {}).get("icon"),
        )
        for item in sorted(row["receipt_items"], key=lambda item: item["id"])
    ]

    return ReceiptDetail(
        id=row["id"],
        store_name=row["store_name"],
        purchase_date=row["purchase_date"],
        total_amount=row["total_amount"],
        vat_amount=row["vat_amount"],
        currency=row["currency"],
        created_at=row["created_at"],
        image_url=_signed_url(db, row["image_path"]) if row["image_path"] else None,
        items=items,
    )


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receipt(receipt_id: UUID, db: Client = Depends(get_user_db)) -> Response:
    """Delete a receipt, its items (via ON DELETE CASCADE) and its photo."""
    row = _get_receipt(db, receipt_id, "id, image_path")

    db.table("receipts").delete().eq("id", row["id"]).execute()

    if row["image_path"]:
        try:
            db.storage.from_(RECEIPTS_BUCKET).remove([row["image_path"]])
        except Exception:
            # The receipt is already gone; a leftover image isn't worth failing for.
            logger.exception("Could not delete image %s", row["image_path"])

    return Response(status_code=status.HTTP_204_NO_CONTENT)
