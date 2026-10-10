# BonScan

AI expense tracker for German supermarket receipts (Rewe, Lidl, Aldi, dm).
Photograph a receipt, and an AI vision model extracts the store, date, items, prices and VAT.
Items are categorised automatically, and a dashboard shows spending by category, store and month,
plus price trends and forecasts.

> Status: project skeleton. The receipt scanning, database and dashboard come in later steps.

## Stack

| Part     | Tech                                         |
| -------- | -------------------------------------------- |
| Backend  | FastAPI (Python 3.11+) in `backend/`         |
| Frontend | React + Vite + Tailwind CSS in `frontend/`   |
| Hosting  | Vercel (frontend), Render (backend)          |

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
cp .env.example .env
uvicorn app.main:app --reload
```

Check it: open http://localhost:8000/api/health. You should see `{"status":"ok","app":"BonScan"}`.
Interactive API docs are at http://localhost:8000/docs.

### 2. Frontend (http://localhost:5173)

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173. It shows **API connected ✅** when the backend is running
and **API not reachable ❌** when it isn't.
