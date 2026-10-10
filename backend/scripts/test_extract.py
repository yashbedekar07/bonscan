"""Run AI extraction on every image in backend/test_receipts/ and print the results.

Lets you tune the prompt without clicking through the UI. Only Gemini is
called: nothing is uploaded to storage or saved to the database.

To stay within the Gemini free tier, the script waits between requests and
stops completely if the rate limit is reached.

Usage (from the backend folder, with the venv active):
    python scripts/test_extract.py                 # all images
    python scripts/test_extract.py rewe_01.jpg     # just one
"""

import json
import sys
import time
from pathlib import Path

# Make the "app" package importable when running this file directly.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import ConfigError  # noqa: E402
from app.extraction import ExtractionError, extract_receipt  # noqa: E402
from app.images import ImageError, prepare_image  # noqa: E402

TEST_DIR = BACKEND_DIR / "test_receipts"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

# Seconds to wait between Gemini calls (free tier allows only a few requests per minute).
PAUSE_SECONDS = 10

# Same names as the categories seeded in supabase/schema.sql. Kept here so the
# script works without logging in to Supabase.
CATEGORY_NAMES = [
    "Groceries",
    "Drugstore & Hygiene",
    "Household",
    "Eating Out",
    "Drinks & Snacks",
    "Transport",
    "Clothing",
    "Electronics",
    "Deposit (Pfand)",
    "Other",
]


def main() -> None:
    # Umlauts and ✓ would crash on some Windows consoles without this.
    sys.stdout.reconfigure(encoding="utf-8")

    if not TEST_DIR.is_dir():
        print(f"Create {TEST_DIR} and put some receipt photos in it.")
        sys.exit(1)

    names = sys.argv[1:]
    images = sorted(
        path
        for path in TEST_DIR.iterdir()
        if path.suffix.lower() in IMAGE_SUFFIXES and (not names or path.name in names)
    )
    if not images:
        print(f"No JPG, PNG or WEBP images found in {TEST_DIR}.")
        sys.exit(1)

    ok = 0
    for index, path in enumerate(images):
        if index > 0:
            print(f"(waiting {PAUSE_SECONDS}s to respect the free-tier rate limit)\n")
            time.sleep(PAUSE_SECONDS)

        print("=" * 70)
        print(path.name)
        print("=" * 70)

        try:
            image = prepare_image(path.read_bytes())
            started = time.perf_counter()
            result = extract_receipt(image.data, image.mime_type, CATEGORY_NAMES)
        except ConfigError as error:
            print(f"Setup problem: {error}")
            sys.exit(1)
        except (ImageError, ExtractionError) as error:
            print(f"FAILED ({error.status_code}): {error.message}\n")
            if error.status_code == 429:
                print("Rate limit reached. Stopping here; try again in a few minutes.")
                break
            continue

        seconds = time.perf_counter() - started
        print(json.dumps(result.draft.model_dump(), indent=2, ensure_ascii=False))

        items_sum = sum(item.total_price for item in result.draft.items)
        print(f"\nItems: {len(result.draft.items)}  |  sum {items_sum:.2f}  |  "
              f"total {result.draft.total_amount}  |  {seconds:.1f}s")
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  ! {warning}")
        else:
            print("No warnings ✓")
            ok += 1
        print()

    print(f"Done: {ok}/{len(images)} receipts without warnings.")


if __name__ == "__main__":
    main()
