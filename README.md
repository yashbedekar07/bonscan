# BonScan

AI expense tracker for German supermarket receipts (Rewe, Lidl, Aldi, dm).
Photograph a receipt, and an AI vision model extracts the store, date, items, prices and VAT.
Items are categorised automatically, and a dashboard shows spending by category, store and month,
plus price trends and forecasts.

> Status: accounts and database are set up. Receipt scanning and the spending dashboard come in later steps.

## Stack

| Part                       | Tech                                                 |
| -------------------------- | ---------------------------------------------------- |
| Backend                    | FastAPI (Python 3.11+) in `backend/`                 |
| Frontend                   | React + Vite + Tailwind CSS + React Router in `frontend/` |
| Database, auth, storage    | Supabase (schema in `supabase/schema.sql`)           |
| Hosting                    | Vercel (frontend), Render (backend)                  |

## How auth works

1. The React app logs users in with Supabase Auth (`@supabase/supabase-js`) using the public **anon** key.
2. For calls to our API, it sends the user's access token as `Authorization: Bearer <token>`.
3. FastAPI checks that token with Supabase (`app/auth.py`) and returns `401` if it's missing or invalid.
4. Row Level Security in the database makes sure each user can only ever see their own receipts and budgets.

## Supabase setup (one time)

1. Create a free project at https://supabase.com/dashboard.
2. **Create the tables:** open **SQL Editor → New query**, paste the whole of
   [`supabase/schema.sql`](supabase/schema.sql) and click **Run**. It is safe to run again.
3. **Get your keys:** open **Project Settings → API Keys** (or **Settings → API** on older dashboards) and note:
   - the **Project URL** (`https://<ref>.supabase.co`, also under **Settings → Data API**)
   - the **anon / publishable** key → frontend
   - the **service_role / secret** key → backend only, never in the frontend or in git
4. **Auth URLs:** open **Authentication → URL Configuration** and set **Site URL** to
   `http://localhost:5173`, so confirmation emails link back to your local app.
5. *(Optional, for quicker local testing)* **Authentication → Sign In / Providers → Email**:
   turn off **Confirm email** to log in right after signing up.

## Environment variables

| File            | Variable                 | Value                                   |
| --------------- | ------------------------ | --------------------------------------- |
| `backend/.env`  | `FRONTEND_ORIGINS`       | `http://localhost:5173`                 |
| `backend/.env`  | `SUPABASE_URL`           | Project URL                             |
| `backend/.env`  | `SUPABASE_SERVICE_KEY`   | service_role / secret key               |
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
| GET    | `/api/health`     | –    | `{"status": "ok", "app": "BonScan"}` |
| GET    | `/api/me`         | ✅   | `{"id": "...", "email": "..."}`  |
| GET    | `/api/categories` | ✅   | list of `{id, name, icon}`       |

## Testing it

1. Open http://localhost:5173. You're sent to **/login** because you're logged out.
2. Click **Sign up**, create an account, then confirm via email (or log in directly if you turned off confirmation).
3. The dashboard shows **Welcome, &lt;your email&gt;** and the 10 categories loaded from the API.
4. **Log out** sends you back to the login page; opening `/dashboard` again redirects to `/login`.
5. Without a token, the API refuses access:
   ```bash
   curl -i http://localhost:8000/api/me    # → 401 Unauthorized
   ```
