"""Fill the BonScan demo account with ~4 months of realistic FAKE receipts.

For the recruiter demo: dashboard, price tracker, forecast, budgets and alerts
all have something to show. Everything here is made up.

Security:
  - Only the public anon key is used, never the service_role / secret key.
  - The script logs in AS the demo user (password asked with getpass: never
    printed, stored or passed on the command line), so Row Level Security makes
    it impossible to read or write anyone else's data.
  - It refuses to run for any account other than demo@bonscan.app.

What it does (each run gives the same data for the same day: fixed random seed):
  1. Deletes ALL receipts (with their items and photos) and budgets of the demo account,
     so running it twice never creates duplicates.
  2. Inserts ~45-60 receipts over the last ~4 months (REWE, Lidl, ALDI SÜD, Edeka, dm,
     Rossmann, a bakery, DB and a pizza/döner place). Built in on purpose:
       - Butter at REWE gets more than 15 % more expensive on the latest shop (price alert),
       - "Eating Out" this month is far above its 3-month average (spending alert),
       - the Eating Out budget is over 80 % used this month (budget alert).
  3. Creates 3 budgets: Groceries, Eating Out, Drugstore & Hygiene.

Usage (Windows CMD, from the backend folder with the venv active):
    python scripts\\seed_demo.py --dry-run     preview only: no login, nothing written
    python scripts\\seed_demo.py               log in, delete old demo data, insert new data
    python scripts\\seed_demo.py --verify      log in and print the numbers the API returns
                                              (needs the backend running, see --api-url)
"""

import argparse
import getpass
import random
import sys
import uuid
import zlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

# Make the "app" package importable when running this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import RECEIPTS_BUCKET, SUPABASE_ANON_KEY, SUPABASE_URL, supabase_configured  # noqa: E402

DEMO_EMAIL = "demo@bonscan.app"  # the ONLY account this script will touch
SEED = 2026  # fixed random seed → same data on every run (for the same day)
DAYS = 118  # about 4 months ending today
SOURCE = {"source": "demo_seed"}  # stored in raw_ai_json
BUDGETS = {"Groceries": 300.00, "Eating Out": 60.00, "Drugstore & Hygiene": 25.00}

# ---------- Products ----------

G, D, H, S, E, T, P = (
    "Groceries", "Drugstore & Hygiene", "Household", "Drinks & Snacks", "Eating Out", "Transport", "Deposit (Pfand)",
)


@dataclass(frozen=True)
class Product:
    category: str
    price: float  # typical price at REWE (per kg for weighed items)
    vat: float  # 7 % for food, 19 % for most other things
    weighed: bool = False
    deposit: float = 0.0  # bottle deposit per item (added as a separate "Pfand" line)
    fixed_price: bool = False  # e.g. the Deutschlandticket: same price everywhere, every month


PRODUCTS = {
    # Groceries (7 % VAT)
    "Bio Vollmilch 1L": Product(G, 1.29, 0.07),
    "Bananen": Product(G, 1.49, 0.07, weighed=True),
    "Toastbrötchen": Product(G, 0.99, 0.07),
    "Butter 250g": Product(G, 1.99, 0.07),
    "Gouda jung 400g": Product(G, 3.49, 0.07),
    "Spaghetti 500g": Product(G, 0.99, 0.07),
    "Tomaten 500g": Product(G, 1.79, 0.07),
    "Äpfel Elstar 1kg": Product(G, 2.49, 0.07),
    "Eier Freiland 10er": Product(G, 2.99, 0.07),
    "Joghurt Natur 500g": Product(G, 0.89, 0.07),
    "Haferflocken 500g": Product(G, 0.79, 0.07),
    "Hähnchenbrust 400g": Product(G, 4.99, 0.07),
    "Kartoffeln 2kg": Product(G, 2.49, 0.07),
    "Vollkornbrot 500g": Product(G, 1.99, 0.07),
    "Paprika rot": Product(G, 0.79, 0.07),
    "Mozzarella 125g": Product(G, 0.99, 0.07),
    "Kaffee Crema 1kg": Product(G, 13.99, 0.07),
    # Drinks & snacks
    "Mineralwasser 1,5L": Product(S, 0.39, 0.19, deposit=0.25),
    "Cola 1,25L": Product(S, 1.19, 0.19, deposit=0.25),
    "Apfelschorle 1L": Product(S, 0.95, 0.19, deposit=0.25),
    "Chips Paprika": Product(S, 1.69, 0.07),
    "Schokolade 100g": Product(S, 1.19, 0.07),
    # Household (19 %)
    "Spülmittel": Product(H, 1.25, 0.19),
    "Küchenrolle 4er": Product(H, 2.79, 0.19),
    "Müllbeutel 35L": Product(H, 1.99, 0.19),
    "Toilettenpapier 8er": Product(H, 3.49, 0.19),
    "Waschmittel 20WL": Product(H, 5.95, 0.19),
    # Drugstore (19 %)
    "Zahnpasta": Product(D, 1.95, 0.19),
    "Duschgel": Product(D, 1.45, 0.19),
    "Shampoo": Product(D, 2.95, 0.19),
    "Deo Spray": Product(D, 2.25, 0.19),
    "Handseife": Product(D, 0.95, 0.19),
    "Taschentücher 10er": Product(D, 1.65, 0.19),
    # Bakery
    "Brötchen": Product(G, 0.45, 0.07),
    "Croissant": Product(G, 1.25, 0.07),
    "Laugenbrezel": Product(G, 0.95, 0.07),
    "Mehrkornbrot": Product(G, 3.20, 0.07),
    # Transport
    "Deutschlandticket": Product(T, 58.00, 0.07, fixed_price=True),
    # Eating out (takeaway, 7 %)
    "Döner Kebab": Product(E, 7.50, 0.07),
    "Dürüm": Product(E, 8.00, 0.07),
    "Pizza Margherita": Product(E, 9.00, 0.07),
    "Pizza Salami": Product(E, 10.50, 0.07),
    "Falafel Teller": Product(E, 9.50, 0.07),
    "Pommes": Product(E, 3.50, 0.07),
    "Ayran": Product(E, 1.80, 0.07),
    "Cola 0,33L": Product(E, 2.50, 0.07),
}

GROCERY_BASICS = ["Bio Vollmilch 1L", "Toastbrötchen", "Spaghetti 500g", "Tomaten 500g", "Äpfel Elstar 1kg",
                  "Eier Freiland 10er", "Joghurt Natur 500g", "Haferflocken 500g", "Kartoffeln 2kg", "Paprika rot",
                  "Mozzarella 125g", "Gouda jung 400g", "Vollkornbrot 500g"]

# Store → (price factor vs REWE, products sold there)
STORES = {
    "REWE": (1.00, GROCERY_BASICS + ["Hähnchenbrust 400g", "Kaffee Crema 1kg", "Mineralwasser 1,5L", "Cola 1,25L",
                                     "Chips Paprika", "Schokolade 100g", "Spülmittel", "Küchenrolle 4er"]),
    "Lidl": (0.92, GROCERY_BASICS + ["Mineralwasser 1,5L", "Apfelschorle 1L", "Schokolade 100g", "Müllbeutel 35L"]),
    "ALDI SÜD": (0.90, GROCERY_BASICS + ["Butter 250g", "Mineralwasser 1,5L", "Chips Paprika", "Toilettenpapier 8er"]),
    "Edeka": (1.08, GROCERY_BASICS + ["Butter 250g", "Hähnchenbrust 400g", "Apfelschorle 1L", "Kaffee Crema 1kg"]),
    "dm-drogerie markt": (1.00, ["Zahnpasta", "Duschgel", "Shampoo", "Deo Spray", "Handseife",
                                 "Taschentücher 10er", "Waschmittel 20WL"]),
    "Rossmann": (1.02, ["Zahnpasta", "Duschgel", "Shampoo", "Deo Spray", "Handseife", "Taschentücher 10er"]),
    "Bäckerei Thürmann": (1.00, ["Croissant", "Laugenbrezel", "Mehrkornbrot"]),
    "DB": (1.00, ["Deutschlandticket"]),
    "Pizza & Döner Express": (1.00, ["Döner Kebab", "Dürüm", "Pizza Margherita", "Pizza Salami", "Falafel Teller"]),
}

# The planned price alert: Butter at REWE, 1,99 € → 2,39 € (+20 %) on the latest REWE shop.
PRICE_RISE_ITEM, PRICE_RISE_STORE, PRICE_BEFORE, PRICE_AFTER = "Butter 250g", "REWE", 1.99, 2.39

# This month's takeaway visits: deliberately more than usual (spending alert + budget > 80 %).
EATING_OUT_THIS_MONTH = [
    ["Döner Kebab", "Ayran"],
    ["Pizza Margherita", "Cola 0,33L"],
    ["Dürüm", "Pommes", "Ayran"],
    ["Pizza Salami", "Falafel Teller", "Cola 0,33L"],
]

# ---------- Data model ----------


@dataclass
class Item:
    name: str
    category: str
    quantity: float
    unit_price: float
    total_price: float
    vat_rate: float


@dataclass
class Receipt:
    id: str
    store: str
    day: date
    items: list[Item] = field(default_factory=list)

    @property
    def total(self) -> float:
        return round(sum(i.total_price for i in self.items), 2)

    @property
    def vat(self) -> float:
        # Prices include VAT: VAT = price − price / (1 + rate)
        return round(sum(i.total_price - i.total_price / (1 + i.vat_rate) for i in self.items if i.total_price > 0), 2)


def store_price(name: str, store: str, day: date) -> float:
    """Price of a product at a store in a given month: store level plus a small monthly change (max ±2 %)."""
    product = PRODUCTS[name]
    if product.fixed_price:
        return product.price
    factor = STORES[store][0]
    # crc32 (not hash()) so the "random" monthly change is the same on every run.
    drift = (-0.02, 0.0, 0.0, 0.02)[zlib.crc32(f"{name}|{store}|{day:%Y-%m}".encode()) % 4]
    return round(product.price * factor * (1 + drift), 2)


# ---------- Generation ----------


def generate(today: date) -> list[Receipt]:
    rnd = random.Random(SEED)
    start = today - timedelta(days=DAYS)
    receipts: list[Receipt] = []

    def new_receipt(store: str, day: date) -> Receipt:
        receipt = Receipt(str(uuid.UUID(int=rnd.getrandbits(128), version=4)), store, day)
        receipts.append(receipt)
        return receipt

    def add(receipt: Receipt, name: str, quantity: float = 1, price: float | None = None) -> None:
        product = PRODUCTS[name]
        unit = price if price is not None else store_price(name, receipt.store, receipt.day)
        receipt.items.append(Item(name, product.category, quantity, unit, round(unit * quantity, 2), product.vat))
        if product.deposit:
            receipt.items.append(Item("Pfand", P, quantity, product.deposit, round(product.deposit * quantity, 2), 0.19))

    def shop(store: str, day: date, low: int, high: int) -> Receipt:
        receipt = new_receipt(store, day)
        for name in rnd.sample(STORES[store][1], rnd.randint(low, high)):
            add(receipt, name, quantity=rnd.choice([1, 1, 1, 2]))
        return receipt

    day = start
    while day <= today:
        week = (day - start).days // 7
        weekday = day.weekday()  # Monday = 0

        if weekday == 5 and week not in (4, 11):  # REWE weekly shop (2 weeks skipped: holidays)
            r = shop("REWE", day, 8, 12)
            add(r, "Bananen", quantity=round(rnd.uniform(0.7, 1.3), 3))
            add(r, PRICE_RISE_ITEM, price=PRICE_BEFORE)  # a regular, fixed price (see below)
        if weekday == 1 and week % 2 == 0:  # Lidl every other Tuesday
            r = shop("Lidl", day, 5, 8)
            add(r, "Bananen", quantity=round(rnd.uniform(0.7, 1.2), 3))
        if weekday == 3 and week % 4 == 1:  # ALDI every 4th Thursday
            shop("ALDI SÜD", day, 3, 5)
        if weekday == 2 and week % 4 == 3:  # Edeka every 4th Wednesday
            shop("Edeka", day, 2, 4)
        if weekday == 4 and week % 4 == 2:  # dm every 4th Friday
            shop("dm-drogerie markt", day, 2, 3)
        if weekday == 0 and week % 5 == 4:  # Rossmann every 5th Monday
            shop("Rossmann", day, 1, 3)
        if weekday == 6 and week % 3 == 1:  # bakery every third Sunday
            r = new_receipt("Bäckerei Thürmann", day)
            add(r, "Brötchen", quantity=rnd.choice([4, 6]))
            add(r, rnd.choice(STORES["Bäckerei Thürmann"][1]))
        if day.day == 1:  # Deutschlandticket on the 1st of each month
            add(new_receipt("DB", day), "Deutschlandticket")
        # Takeaway: twice a month in earlier months (this month is handled below).
        if day.day in (9, 23) and (day.year, day.month) != (today.year, today.month):
            r = new_receipt("Pizza & Döner Express", day)
            add(r, rnd.choice(STORES["Pizza & Döner Express"][1]))
            add(r, rnd.choice(["Ayran", "Cola 0,33L"]))
        day += timedelta(days=1)

    # This month: four takeaway visits, spread over the days so far.
    for index, order in enumerate(EATING_OUT_THIS_MONTH):
        visit_day = today.replace(day=max(1, round(today.day * (index + 1) / len(EATING_OUT_THIS_MONTH))))
        r = new_receipt("Pizza & Döner Express", visit_day)
        for name in order:
            add(r, name)

    # The price alert: on the latest REWE shop, Butter costs 2,39 € instead of 1,99 €.
    latest_rewe = max((r for r in receipts if r.store == PRICE_RISE_STORE), key=lambda r: r.day)
    for item in latest_rewe.items:
        if item.name == PRICE_RISE_ITEM:
            item.unit_price = item.total_price = PRICE_AFTER

    return sorted(receipts, key=lambda r: (r.day, r.store))


# ---------- Printing ----------


def money(amount: float) -> str:
    return f"{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def print_summary(receipts: list[Receipt]) -> None:
    by_month: dict[str, list[Receipt]] = defaultdict(list)
    for r in receipts:
        by_month[r.day.strftime("%Y-%m")].append(r)
    for month, group in sorted(by_month.items()):
        print(f"  {month}: {len(group):3d} receipts, {sum(len(r.items) for r in group):4d} items, "
              f"{money(sum(r.total for r in group)):>11}")
    print(f"  Receipts: {len(receipts)} | items: {sum(len(r.items) for r in receipts)} | "
          f"dates: {receipts[0].day:%d.%m.%Y} – {receipts[-1].day:%d.%m.%Y} | "
          f"total spent: {money(sum(r.total for r in receipts))}")


def preview_insights(receipts: list[Receipt], today: date) -> None:
    """Run the backend's own analytics/insights code on the generated data (no database)."""
    from app import analytics
    from app.services import forecast, insights

    items = [
        {"name": i.name, "quantity": i.quantity, "unit_price": i.unit_price, "total_price": i.total_price,
         "categories": {"name": i.category, "icon": None},
         "receipts": {"id": r.id, "store_name": r.store, "purchase_date": r.day.isoformat()}}
        for r in receipts for i in r.items
    ]
    current = today.strftime("%Y-%m")
    first = receipts[0].day.strftime("%Y-%m")
    this_month = analytics.category_totals(items, current)
    history = [analytics.category_totals(items, m) for m in forecast.complete_months(current, first)]
    budgets = [{"name": n, "limit": l, "spent": max(this_month.get(n, 0.0), 0.0),
                "projected": forecast.project_month_end(max(this_month.get(n, 0.0), 0.0), today)}
               for n, l in BUDGETS.items()]
    alerts = (insights.budget_alerts(budgets)
              + insights.category_spikes({k: v for k, v in this_month.items() if v > 0}, history)
              + insights.price_increases(items, today))
    print("\nAlerts the dashboard should show:")
    for alert in insights.sort_alerts(alerts):
        print(f"  [{alert['type']}] {alert['message']}")


# ---------- Supabase ----------


def log_in(email: str):
    """Log in as the demo user. Returns (auth client, user id, Supabase client acting as that user)."""
    if email != DEMO_EMAIL:
        sys.exit(f"Refusing to run: this script only works with {DEMO_EMAIL}.")
    if not supabase_configured():
        sys.exit("Set SUPABASE_URL and SUPABASE_ANON_KEY in backend/.env first.")

    from supabase import create_client  # imported here so --dry-run works without Supabase

    from app.supabase_client import user_client

    password = getpass.getpass(f"Password for {email} (not shown): ")
    auth = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)  # anon key only
    try:
        response = auth.auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        sys.exit("Login failed: check the password (and that the account's email is confirmed).")
    finally:
        del password  # don't keep it around
    if response.user is None or response.user.email != DEMO_EMAIL:
        sys.exit("Login returned a different account. Nothing was changed.")
    print(f"Logged in as {email} (user {response.user.id}).")
    return auth, response.user.id, user_client(response.session.access_token), response.session.access_token


def fetch_all(build_query) -> list[dict]:
    rows, start = [], 0
    while True:
        page = build_query().range(start, start + 999).execute().data
        rows.extend(page)
        if len(page) < 1000:
            return rows
        start += 1000


def seed(db, user_id: str, receipts: list[Receipt]) -> None:
    # 1. Categories: map names to ids, fail clearly if one is missing.
    category_ids = {row["name"]: row["id"] for row in db.table("categories").select("id, name").execute().data}
    needed = {i.category for r in receipts for i in r.items} | set(BUDGETS)
    missing = sorted(needed - category_ids.keys())
    if missing:
        sys.exit(f"These categories are missing in the database: {', '.join(missing)}. "
                 "Run supabase/schema.sql in the Supabase SQL Editor. Nothing was changed.")

    # 2. Delete the demo account's old data (RLS: only this user's rows are visible/deletable).
    old = fetch_all(lambda: db.table("receipts").select("id, image_path").eq("user_id", user_id).order("id"))
    photos = [row["image_path"] for row in old if row["image_path"]]
    if photos:
        db.storage.from_(RECEIPTS_BUCKET).remove(photos)
    if old:
        db.table("receipts").delete().eq("user_id", user_id).execute()  # items go too (ON DELETE CASCADE)
    db.table("budgets").delete().eq("user_id", user_id).execute()
    print(f"Deleted {len(old)} old receipts ({len(photos)} photos) and the old budgets of the demo account.")

    # 3. Insert receipts and items (ids are generated here, so two requests are enough).
    db.table("receipts").insert([
        {"id": r.id, "user_id": user_id, "store_name": r.store, "purchase_date": r.day.isoformat(),
         "total_amount": r.total, "vat_amount": r.vat, "currency": "EUR", "image_path": None, "raw_ai_json": SOURCE}
        for r in receipts
    ]).execute()
    items = [
        {"receipt_id": r.id, "name": i.name, "quantity": i.quantity, "unit_price": i.unit_price,
         "total_price": i.total_price, "category_id": category_ids[i.category]}
        for r in receipts for i in r.items
    ]
    db.table("receipt_items").insert(items).execute()

    # 4. Budgets.
    db.table("budgets").insert([
        {"user_id": user_id, "category_id": category_ids[name], "monthly_limit": limit}
        for name, limit in BUDGETS.items()
    ]).execute()

    print(f"\nInserted {len(receipts)} receipts and {len(items)} items, "
          f"{receipts[0].day:%d.%m.%Y} – {receipts[-1].day:%d.%m.%Y}, "
          f"total spent {money(sum(r.total for r in receipts))}.")
    print("Budgets: " + ", ".join(f"{name} {money(limit)}" for name, limit in BUDGETS.items()))


def verify(api_url: str, token: str) -> bool:
    """Call the real API as the demo user and print the key numbers. Returns True if every call worked."""
    import httpx

    headers = {"Authorization": f"Bearer {token}"}
    client = httpx.Client(base_url=api_url.rstrip("/"), headers=headers, timeout=90)
    ok = True

    def get(path: str, **params):
        nonlocal ok
        try:
            response = client.get(path, params=params)
            response.raise_for_status()
            return response
        except Exception as error:
            ok = False
            detail = getattr(getattr(error, "response", None), "text", "") or str(error)
            print(f"  ✗ GET {path}: {detail[:200]}")
            return None

    print(f"\nChecking the API at {api_url} as {DEMO_EMAIL} …")
    if (r := get("/api/health")) is None:
        print("  Is the backend running? Start it with: uvicorn app.main:app --reload")
        return False

    if r := get("/api/analytics/summary"):
        s = r.json()
        change = "n/a" if s["change_percent"] is None else f"{s['change_percent']:+.1f} %"
        print(f"  Summary {s['month']}: spent {money(s['total_spent'])} (last month {money(s['previous_month_total'])},"
              f" {change}), {s['receipt_count']} receipts, avg {money(s['average_per_receipt'] or 0)},"
              f" top store {(s['top_store'] or {}).get('store')}, biggest category {(s['biggest_category'] or {}).get('name')}")
    if r := get("/api/analytics/by-category"):
        print("  By category: " + ", ".join(f"{c['name']} {money(c['amount'])} ({c['percent']} %)" for c in r.json()))
    if r := get("/api/analytics/by-store"):
        print("  By store: " + ", ".join(f"{s['store']} {money(s['amount'])}/{s['visits']}×" for s in r.json()))
    if r := get("/api/analytics/monthly-trend", months=5):
        print("  Trend: " + ", ".join(f"{m['month']} {money(m['total'])}" for m in r.json()))
    if r := get("/api/analytics/top-items", limit=3):
        top = r.json()
        print("  Top items by spend: " + ", ".join(f"{t['name']} {money(t['total_spent'])}" for t in top["by_spend"]))
        print("  Top items by count: " + ", ".join(f"{t['name']} {t['times_bought']}×" for t in top["by_count"]))
    if r := get("/api/analytics/price-history", item="butter"):
        points = [p for p in r.json()["points"] if p["store"] == PRICE_RISE_STORE][-2:]
        print("  Butter at REWE, last two prices: " + " → ".join(f"{money(p['price'])} ({p['date']})" for p in points))
    if r := get("/api/budgets/progress"):
        print("  Budgets: " + ", ".join(f"{b['category_name']} {money(b['spent'])}/{money(b['monthly_limit'])}"
                                        f" = {b['percent']} % ({b['status']})" for b in r.json()))
    if r := get("/api/insights/forecast"):
        f = r.json()
        nxt = f["next_month"]
        print(f"  Forecast: spent {money(f['spent_so_far'])} in {f['days_passed']}/{f['days_in_month']} days →"
              f" about {money(f['projected_total'])} this month; {nxt['month']}: "
              f"{money(nxt['forecast']) if nxt['forecast'] is not None else nxt['message']}")
    if r := get("/api/insights/alerts"):
        print("  Alerts:")
        for alert in r.json():
            print(f"    [{alert['type']}] {alert['message']}")
    if r := get("/api/receipts"):
        receipts = r.json()
        print(f"  My receipts: {len(receipts)} listed")
        if receipts and (d := get(f"/api/receipts/{receipts[0]['id']}")):
            detail = d.json()
            print(f"  Receipt detail ({detail['store_name']}): {len(detail['items'])} items, "
                  f"has_image={detail['has_image']}, image_url={detail['image_url']}")
    if r := get("/api/export/csv", **{"from": "2000-01-01", "to": date.today().isoformat()}):
        print(f"  CSV export: {len(r.text.strip().splitlines()) - 1} item rows")

    # Delete without an image: create a throwaway receipt, then delete it again.
    try:
        created = client.post("/api/receipts", json={
            "store_name": "Verify test", "purchase_date": date.today().isoformat(), "total_amount": 1.0,
            "items": [{"name": "Test", "total_price": 1.0, "category": "Other"}], "raw_ai_json": SOURCE})
        created.raise_for_status()
        deleted = client.delete(f"/api/receipts/{created.json()['id']}")
        deleted.raise_for_status()
        print("  Delete without image: OK (temporary receipt created and deleted)")
    except Exception as error:
        ok = False
        print(f"  ✗ Delete without image failed: {error}")

    print("\nAll API checks passed ✓" if ok else "\nSome API checks failed (see ✗ above).")
    return ok


# ---------- Main ----------


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # umlauts and € on Windows consoles
    parser = argparse.ArgumentParser(description=f"Reset and fill the demo account {DEMO_EMAIL} with fake receipts.")
    parser.add_argument("--email", default=DEMO_EMAIL, help=f"must be {DEMO_EMAIL}")
    parser.add_argument("--dry-run", action="store_true", help="only show the generated data, no login")
    parser.add_argument("--verify", action="store_true", help="only check the numbers via the API (no changes)")
    parser.add_argument("--api-url", default="http://localhost:8000", help="backend for --verify / the check after seeding")
    args = parser.parse_args()

    if args.email != DEMO_EMAIL:
        sys.exit(f"Refusing to run: this script only works with {DEMO_EMAIL}.")

    today = date.today()
    receipts = generate(today)

    if args.dry_run:
        print(f"Demo data for {DEMO_EMAIL} (dry run, nothing is written):")
        print_summary(receipts)
        preview_insights(receipts, today)
        return

    auth, user_id, db, token = log_in(args.email)
    try:
        if not args.verify:
            seed(db, user_id, receipts)
        verify(args.api_url, token)
    finally:
        auth.auth.sign_out()


if __name__ == "__main__":
    main()
