"""Fill a demo account with ~3 months of realistic FAKE receipts (no images).

Made for the recruiter demo: the dashboard, forecast and alerts then have
something to show. The data is generated, not real, and includes a few
things on purpose so the insights have something to say:
  - Butter at REWE gets more expensive this month (price alert),
  - a party shop this month with lots of drinks and snacks (category alert),
  - bottle deposit (Pfand) and returns (Leergut), and the odd discount.

Safety:
  - No service key. The script logs in AS the demo user (DEMO_EMAIL /
    DEMO_PASSWORD from backend/.env), so Row Level Security makes it
    impossible to write anyone else's data.
  - It checks that this login really belongs to --user-id before writing.
  - Every receipt it creates is marked {"demo": true} in raw_ai_json, and
    --replace only ever deletes those marked receipts.

Usage (from the backend folder, venv active):
    python scripts/seed_demo.py --user-id <uuid> --dry-run    # preview, no login, writes nothing
    python scripts/seed_demo.py --user-id <uuid>              # insert
    python scripts/seed_demo.py --user-id <uuid> --replace    # delete earlier demo receipts first
"""

import argparse
import os
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

# Make the "app" package importable when running this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import SUPABASE_ANON_KEY, SUPABASE_URL, supabase_configured  # noqa: E402  (also loads .env)

FULL_MONTHS = 3  # complete months before the current one (so forecasts and alerts have history)
DEMO_MARKER = {"demo": True, "generator": "scripts/seed_demo.py"}

# Product catalogue: (name, category, price, VAT rate). Prices are typical, not real.
G, D, H, S, E, P = "Groceries", "Drugstore & Hygiene", "Household", "Drinks & Snacks", "Eating Out", "Deposit (Pfand)"
FOOD, STANDARD = 0.07, 0.19

CATALOGUE = {
    "REWE": [
        ("Vollmilch 3,5% 1L", G, 1.19, FOOD), ("Gouda jung", G, 1.89, FOOD), ("Vollkornbrot", G, 2.49, FOOD),
        ("Spaghetti 500g", G, 0.99, FOOD), ("Hähnchenbrust 400g", G, 4.99, FOOD), ("Joghurt Natur", G, 0.79, FOOD),
        ("Eier Freiland 10er", G, 2.99, FOOD), ("Tomaten 500g", G, 1.99, FOOD), ("Äpfel Elstar 1kg", G, 2.49, FOOD),
        ("Kaffee Crema 1kg", G, 13.99, FOOD), ("Chips Paprika", S, 1.79, FOOD), ("Spülmittel", H, 1.49, STANDARD),
        ("Küchenrolle 4er", H, 2.99, STANDARD),
    ],
    "Lidl": [
        ("Milch 1,5% 1L", G, 0.99, FOOD), ("Haferflocken 500g", G, 0.89, FOOD), ("Toastbrot", G, 1.29, FOOD),
        ("Mozzarella", G, 0.89, FOOD), ("Paprika rot 3er", G, 1.99, FOOD), ("Schokolade Vollmilch", S, 0.99, FOOD),
        ("Müllbeutel 35L", H, 1.99, STANDARD), ("Frischkäse", G, 0.99, FOOD),
    ],
    "ALDI SÜD": [
        ("Eier 10er", G, 2.49, FOOD), ("Hackfleisch gemischt 500g", G, 3.99, FOOD), ("Kartoffeln 2kg", G, 2.29, FOOD),
        ("Orangensaft 1L", S, 1.49, FOOD), ("Toilettenpapier 8er", H, 3.49, STANDARD), ("Gurke", G, 0.69, FOOD),
        ("Butter 250g", G, 1.99, FOOD),
    ],
    "dm-drogerie markt": [
        ("Zahnpasta", D, 0.95, STANDARD), ("Duschgel", D, 1.25, STANDARD), ("Shampoo", D, 2.45, STANDARD),
        ("Deo Spray", D, 1.95, STANDARD), ("Waschmittel 20WL", H, 4.95, STANDARD), ("Taschentücher", D, 1.75, STANDARD),
        ("Vitamin C Brausetabletten", D, 2.95, STANDARD),
    ],
    "Bäckerei Kamps": [
        ("Croissant", G, 1.20, FOOD), ("Butterbrezel", G, 1.60, FOOD), ("Kaffee to go", E, 2.50, FOOD),
        ("Belegtes Brötchen", E, 3.40, FOOD),
    ],
}


@dataclass
class Item:
    name: str
    category: str
    quantity: float
    unit_price: float | None
    total_price: float
    vat_rate: float


@dataclass
class Receipt:
    store: str
    day: date
    items: list[Item] = field(default_factory=list)

    def add(self, name: str, category: str, price: float, vat: float, quantity: float = 1) -> None:
        self.items.append(Item(name, category, quantity, price, round(price * quantity, 2), vat))

    @property
    def total(self) -> float:
        return round(sum(i.total_price for i in self.items), 2)

    @property
    def vat(self) -> float:
        # VAT is included in German prices: VAT = price - price / (1 + rate)
        return round(sum(i.total_price - i.total_price / (1 + i.vat_rate) for i in self.items if i.total_price > 0), 2)


def generate(today: date) -> list[Receipt]:
    """Create fake receipts from the 1st of the month 3 months ago up to today (same output for the same day)."""
    rnd = random.Random(42)
    this_month = today.replace(day=1)
    start = this_month
    for _ in range(FULL_MONTHS):
        start = (start - timedelta(days=1)).replace(day=1)  # first day of the previous month
    receipts: list[Receipt] = []

    def pick(store: str, low: int, high: int, receipt: Receipt) -> None:
        for name, category, price, vat in rnd.sample(CATALOGUE[store], rnd.randint(low, high)):
            receipt.add(name, category, price, vat, quantity=rnd.choice([1, 1, 1, 2]))

    day = start
    while day <= today:
        weekday = day.weekday()  # Monday = 0
        week = (day - start).days // 7

        if weekday == 5:  # Saturday: weekly big shop at REWE
            r = Receipt("REWE", day)
            pick("REWE", 7, 11, r)
            r.add("Butter 250g", G, 2.29, FOOD)  # a regular; gets pricier on the last shop (see below)
            r.add("Bananen", G, 1.69, FOOD, quantity=round(rnd.uniform(0.8, 1.4), 3))
            r.add("Mineralwasser 6x1,5L", S, 3.49, FOOD)
            r.add("Pfand", P, 1.50, STANDARD)
            if week % 3 == 0:
                r.add("Leergut", P, -3.00, STANDARD)  # returned bottles
            if rnd.random() < 0.3:
                r.add("Rabatt Treuepunkte", G, -0.50, FOOD)
            receipts.append(r)

        if weekday == 2 and week % 2 == 0:  # every other Wednesday: Lidl
            r = Receipt("Lidl", day)
            pick("Lidl", 4, 7, r)
            r.add("Bananen", G, 1.49, FOOD, quantity=round(rnd.uniform(0.7, 1.2), 3))
            receipts.append(r)

        if weekday == 0 and week % 2 == 1:  # every other Monday: ALDI
            r = Receipt("ALDI SÜD", day)
            pick("ALDI SÜD", 3, 6, r)
            receipts.append(r)

        if weekday == 3 and week % 2 == 1:  # every other Thursday: dm
            r = Receipt("dm-drogerie markt", day)
            pick("dm-drogerie markt", 2, 4, r)
            receipts.append(r)

        if weekday in (1, 4, 6) and rnd.random() < 0.7:  # bakery a few mornings a week
            r = Receipt("Bäckerei Kamps", day)
            r.add("Brötchen", G, 0.45, FOOD, quantity=rnd.choice([2, 4, 6]))
            pick("Bäckerei Kamps", 0, 2, r)
            receipts.append(r)

        day += timedelta(days=1)

    # Party shop early this month: lots of drinks & snacks (category alert).
    party_day = min(today, this_month + timedelta(days=3))
    party = Receipt("REWE", party_day)
    party.add("Bier Kasten 20x0,5L", S, 14.99, STANDARD, quantity=2)
    party.add("Pfand Kasten", P, 3.10, STANDARD, quantity=2)
    party.add("Cola 1,5L", S, 1.29, FOOD, quantity=4)
    party.add("Pfand", P, 0.25, STANDARD, quantity=4)
    party.add("Chips Paprika", S, 1.79, FOOD, quantity=3)
    party.add("Rotwein", S, 5.99, STANDARD, quantity=2)
    party.add("Salzstangen", S, 0.99, FOOD, quantity=2)
    receipts.append(party)

    # Price alert: Butter at REWE costs 2,79 € instead of 2,29 € on the most recent shop.
    last_rewe = max((r for r in receipts if r.store == "REWE" and any(i.name == "Butter 250g" for i in r.items)),
                    key=lambda r: r.day)
    for item in last_rewe.items:
        if item.name == "Butter 250g":
            item.unit_price = item.total_price = 2.79

    return sorted(receipts, key=lambda r: (r.day, r.store))


def print_summary(receipts: list[Receipt]) -> None:
    by_month: dict[str, list[Receipt]] = defaultdict(list)
    for r in receipts:
        by_month[r.day.strftime("%Y-%m")].append(r)
    for month, group in sorted(by_month.items()):
        total = sum(r.total for r in group)
        stores = ", ".join(sorted({r.store for r in group}))
        print(f"  {month}: {len(group):3d} receipts, {sum(len(r.items) for r in group):4d} items, "
              f"{total:9.2f} EUR  ({stores})")
    print(f"  Total: {len(receipts)} receipts, {sum(len(r.items) for r in receipts)} items, "
          f"{sum(r.total for r in receipts):.2f} EUR")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # umlauts on Windows consoles
    parser = argparse.ArgumentParser(description="Insert fake demo receipts for ONE demo user.")
    parser.add_argument("--user-id", required=True, help="Supabase user id (uuid) of the demo account")
    parser.add_argument("--replace", action="store_true", help="delete this user's earlier DEMO receipts first")
    parser.add_argument("--dry-run", action="store_true", help="only show what would be inserted")
    args = parser.parse_args()

    receipts = generate(date.today())
    print(f"Generated {len(receipts)} fake receipts ({FULL_MONTHS} full months + this month so far):")
    print_summary(receipts)

    if args.dry_run:
        print("\nDry run: nothing was written.")
        return

    # --- Log in as the demo user (no service key) ---
    email, password = os.getenv("DEMO_EMAIL", "").strip(), os.getenv("DEMO_PASSWORD", "")
    if not supabase_configured() or not email or not password:
        sys.exit("Set SUPABASE_URL, SUPABASE_ANON_KEY, DEMO_EMAIL and DEMO_PASSWORD in backend/.env first.")

    from supabase import create_client  # imported here so --dry-run works without Supabase

    from app.supabase_client import user_client

    auth_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    try:
        session = auth_client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as error:
        sys.exit(f"Login as the demo user failed: {error}")

    if session.user is None or session.user.id != args.user_id:
        auth_client.auth.sign_out()
        sys.exit("The DEMO_EMAIL login does not belong to --user-id. Nothing was written.")

    db = user_client(session.session.access_token)  # Row Level Security: only this user's rows
    print(f"\nLogged in as {email} (user {args.user_id}).")

    try:
        # --- Earlier demo data ---
        existing = (
            db.table("receipts").select("id", count="exact").eq("raw_ai_json->>demo", "true").execute().count or 0
        )
        if existing and not args.replace:
            sys.exit(f"This user already has {existing} demo receipts. Run again with --replace to recreate them.")
        if existing:
            db.table("receipts").delete().eq("raw_ai_json->>demo", "true").execute()
            print(f"Deleted {existing} earlier demo receipts (and their items). Other receipts were not touched.")

        # --- Insert ---
        category_ids = {row["name"]: row["id"] for row in db.table("categories").select("id, name").execute().data}
        missing = {i.category for r in receipts for i in r.items} - category_ids.keys()
        if missing:
            sys.exit(f"Categories missing in the database: {', '.join(sorted(missing))}. Run supabase/schema.sql.")

        for number, r in enumerate(receipts, start=1):
            row = db.table("receipts").insert({
                "user_id": args.user_id,
                "store_name": r.store,
                "purchase_date": r.day.isoformat(),
                "total_amount": r.total,
                "vat_amount": r.vat,
                "currency": "EUR",
                "image_path": None,
                "raw_ai_json": DEMO_MARKER,
            }).execute().data[0]
            db.table("receipt_items").insert([
                {
                    "receipt_id": row["id"],
                    "name": i.name,
                    "quantity": i.quantity,
                    "unit_price": i.unit_price,
                    "total_price": i.total_price,
                    "category_id": category_ids[i.category],
                }
                for i in r.items
            ]).execute()
            print(f"\r  Inserted {number}/{len(receipts)} receipts", end="", flush=True)

        print(f"\nDone: inserted {len(receipts)} demo receipts for user {args.user_id}.")
    finally:
        auth_client.auth.sign_out()


if __name__ == "__main__":
    main()
