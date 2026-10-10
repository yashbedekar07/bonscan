# BonScan

AI expense tracker for German supermarket receipts (Rewe, Lidl, Aldi, dm).
Photograph a receipt, and an AI vision model extracts the store, date, items, prices and VAT.
Items are categorised automatically, and a dashboard shows spending by category, store and month,
plus price trends and forecasts.

> Status: receipt scanning, analytics dashboard, budgets, forecasts, alerts and CSV export work.
> Deployment comes in the next step.

## Stack

| Part                       | Tech                                                 |
| -------------------------- | ---------------------------------------------------- |
| Backend                    | FastAPI (Python 3.11+) in `backend/`                 |
| Frontend                   | React + Vite + Tailwind CSS + React Router + Recharts in `frontend/` |
| Database, auth, storage    | Supabase (schema in `supabase/schema.sql`)           |
| Receipt AI                 | Google Gemini Flash (`google-genai`, structured JSON output) |
| Hosting                    | Vercel (frontend), Render (backend)                  |

## How auth works

1. The React app logs users in with Supabase Auth (`@supabase/supabase-js`) using the public **anon** key.
2. For calls to our API, it sends the user's access token as `Authorization: Bearer <token>`.
3. FastAPI checks that token with Supabase (`app/auth.py`) and returns `401` if it's missing or invalid.
4. The backend then talks to Supabase **as that user** (same token, `app/supabase_client.py`), so
   Row Level Security and the storage policies always apply. The backend never needs the service-role key.
5. If a setting is missing, the API returns a clear `503` and `/api/health` reports what's not configured;
   the frontend shows a setup screen if its own `.env` is incomplete.

## Supabase setup (one time)

1. Create a free project at https://supabase.com/dashboard.
2. **Create the tables:** open **SQL Editor → New query**, paste the whole of
   [`supabase/schema.sql`](supabase/schema.sql) and click **Run**. It is safe to run again.
3. **Get your keys:** open **Project Settings → API Keys** (or **Settings → API** on older dashboards) and note:
   - the **Project URL** (`https://<ref>.supabase.co`, also under **Settings → Data API**)
   - the **anon / publishable** key → both frontend and backend
   - you do **not** need the service_role / secret key
4. **Auth URLs:** open **Authentication → URL Configuration** and set **Site URL** to
   `http://localhost:5173`, so confirmation emails link back to your local app.
5. *(Optional, for quicker local testing)* **Authentication → Sign In / Providers → Email**:
   turn off **Confirm email** to log in right after signing up.

## Environment variables

| File            | Variable                 | Value                                   |
| --------------- | ------------------------ | --------------------------------------- |
| `backend/.env`  | `FRONTEND_ORIGINS`       | `http://localhost:5173,http://127.0.0.1:5173` |
| `backend/.env`  | `SUPABASE_URL`           | Project URL                             |
| `backend/.env`  | `SUPABASE_ANON_KEY`      | anon / publishable key                  |
| `backend/.env`  | `GEMINI_API_KEY`         | key from https://aistudio.google.com/apikey |
| `backend/.env`  | `GEMINI_MODEL`           | `gemini-flash-latest` (or a pinned Flash model) |
| `backend/.env`  | `GEMINI_TIMEOUT_SECONDS` | `60`                                    |
| `frontend/.env` | `VITE_API_URL`           | `http://localhost:8000`                 |
| `frontend/.env` | `VITE_SUPABASE_URL`      | Project URL                             |
| `frontend/.env` | `VITE_SUPABASE_ANON_KEY` | anon / publishable key                  |

Both folders have a `.env.example` to copy from. `.env` files are git-ignored.

## Run locally

You need Python 3.11+ and Node.js 20+. Use two terminals, one for each part.

### 1. Backend (http://localhost:8000)

```bash
cd backend
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Windows (Git Bash):    source .venv/Scripts/activate
# macOS / Linux:         source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then fill in the Supabase values
uvicorn app.main:app --reload
```

Interactive API docs are at http://localhost:8000/docs.

### 2. Frontend (http://localhost:5173)

```bash
cd frontend
npm install
cp .env.example .env    # then fill in the Supabase values
npm run dev
```

## API

| Method | Path              | Auth | Returns                          |
| ------ | ----------------- | ---- | -------------------------------- |
| GET    | `/api/health`     | –    | `{"status": "ok", "app": "BonScan", "supabase_configured": true, "gemini_configured": true}` |
| GET    | `/api/me`         | ✅   | `{"id": "...", "email": "..."}`  |
| GET    | `/api/categories` | ✅   | list of `{id, name, icon}`       |
| POST   | `/api/receipts/extract` | ✅ | upload a photo (`file`), get the AI draft + warnings (not saved) |
| POST   | `/api/receipts`   | ✅   | save a reviewed receipt and its items |
| GET    | `/api/receipts`   | ✅   | your receipts, newest first, with item count |
| GET    | `/api/receipts/{id}` | ✅ | one receipt with items and a 10-minute image link |
| DELETE | `/api/receipts/{id}` | ✅ | delete a receipt, its items and its photo |
| GET    | `/api/analytics/summary?month=YYYY-MM` | ✅ | total, % vs previous month, receipts, average, top store, biggest category |
| GET    | `/api/analytics/by-category?month=YYYY-MM` | ✅ | spending per category (amount, %) |
| GET    | `/api/analytics/by-store?month=YYYY-MM` | ✅ | spending and visits per store |
| GET    | `/api/analytics/monthly-trend?months=12` | ✅ | total per month, empty months included |
| GET    | `/api/analytics/top-items?month=YYYY-MM&limit=10` | ✅ | top items by spend and by count |
| GET    | `/api/analytics/price-history?item=milch` | ✅ | an item's price over time per store |

| GET    | `/api/budgets` | ✅ | your monthly budgets |
| PUT    | `/api/budgets/{category_id}` | ✅ | set/update a limit: `{"monthly_limit": 200}` (must be > 0) |
| DELETE | `/api/budgets/{category_id}` | ✅ | remove a budget |
| GET    | `/api/budgets/progress?month=YYYY-MM` | ✅ | spent vs limit per budget (ok / warning / over) |
| GET    | `/api/insights/forecast` | ✅ | end-of-month projection + next-month forecast |
| GET    | `/api/insights/alerts` | ✅ | plain-language alerts with the numbers behind them |
| GET    | `/api/export/csv?from=YYYY-MM-DD&to=YYYY-MM-DD` | ✅ | CSV for German Excel (`;`, comma decimals) |

## Forecasts and alerts

Plain Python in `backend/app/services/` (pandas/numpy are blocked by Windows Smart App Control on the dev machine).

- **End-of-month projection:** `spent so far ÷ days passed (incl. today) × days in month`.
- **Next month:** `0.5 × last month + 0.3 × the month before + 0.2 × the one before`, using complete months only.
  Months before your first receipt are missing data (weights are rescaled); fewer than 2 months → "not enough data yet".
- **Category alert:** this month > 130 % of the average of the previous 3 months **and** at least 10 € more.
- **Budget alert:** ≥ 80 % used (warning), over 100 % (warning), or projected to go over (info).
- **Price alert:** same item, same store, latest price > 15 % (and ≥ 5 ct) above the previous purchase, within the last 60 days.
- **CSV export:** text cells starting with `=`, `+`, `-` or `@` get a `'` prefix so Excel never runs them as formulas.

### Running the tests (Windows CMD)

```bat
cd /d D:\Project\bonscan\backend
.venv\Scripts\activate.bat
pip install -r requirements-dev.txt
python -m pytest -v
```

## How the dashboard numbers are calculated

The maths is in `backend/app/analytics.py` (plain Python, so it runs anywhere; pandas was
dropped because Windows Smart App Control blocks its native files on the dev machine).

- **Total, store and trend numbers** use the receipt totals (what you actually paid).
- **Category and item numbers** use item prices. They can differ from the totals by a few cents.
- **Discounts and returned deposit** are negative items and reduce their category; categories
  that end up at 0 or below are hidden, and percentages are of the remaining categories.
- **Top items** leave out discounts and bottle deposit. Similar names are grouped
  ("H-Milch 3,5% 1L" and "H-MILCH 3,5%" → "h milch"). "Bought" counts receipt lines.
- **Price tracker** matches whole words ("milch" finds "H-Milch" but not "Vollmilch") and uses the
  price per unit (or per kg). The matched item names are listed under the chart.
- **Store names** are grouped ignoring upper/lower case and extra spaces ("REWE" = "Rewe").

## How receipt scanning works

1. **Upload** (`app/images.py`): the photo is checked with Pillow (JPG, PNG or WEBP, max 10 MB).
   HEIC isn't accepted; iPhones convert photos to JPEG automatically because the upload form only
   accepts JPG/PNG/WEBP. The file is stored privately at `receipts/<user_id>/<uuid>.<ext>`.
2. **Extract** (`app/extraction.py`): Gemini reads the photo using a prompt with German receipt rules
   (comma decimals, SUMME, MwSt lines, Pfand, Rabatt, …) and returns JSON that must match a Pydantic schema.
   Categories are limited to the names in the database.
3. **Check**: if the items don't add up to the total (± 0.05 €), the user gets a warning instead of an error.
4. **Review** (frontend): the user corrects the draft next to the photo and saves it.

### Testing extraction without the UI

Put receipt photos in `backend/test_receipts/` (git-ignored, because real receipts are private), then:

```bash
cd backend
python scripts/test_extract.py              # all images
python scripts/test_extract.py rewe.jpg     # one image
```

It prints the extracted JSON and any warnings for each receipt.

The script calls only Gemini (no Supabase login needed), waits 10 seconds between receipts to stay
within the free-tier rate limit, and stops if the limit is reached anyway.

## Testing it

1. Open http://localhost:5173. You're sent to **/login** because you're logged out.
2. Click **Sign up**, create an account, then confirm via email (or log in directly if you turned off confirmation).
3. The dashboard shows **Welcome, &lt;your email&gt;** and the 10 categories loaded from the API.
4. **Scan receipt**: drop a receipt photo, click **Read receipt**, then check and save it on the review page.
5. **My receipts**: open a saved receipt to see its photo and items; delete it to remove everything.
6. **Log out** sends you back to the login page; opening `/dashboard` again redirects to `/login`.
7. Without a token, the API refuses access:
   ```bash
   curl -i http://localhost:8000/api/me    # → 401 Unauthorized
   ```
