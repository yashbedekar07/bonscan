# BonScan – AI Expense Tracker with Receipt Scanning

## What it is
Users photograph German supermarket receipts (Rewe, Lidl, Aldi, dm). An AI vision model
extracts store, date, items, prices and VAT. Items are categorised automatically, and a
dashboard shows spending by category, store and month, plus price trends and forecasts.

## Stack
- Backend: FastAPI (Python 3.11+), in /backend
- Frontend: React + Vite + Tailwind CSS + Recharts, in /frontend
- Database, auth, image storage: Supabase (added in a later step)
- AI: Gemini Flash API (free tier) for receipt extraction (added in a later step)
- Hosting: Vercel (frontend), Render (backend)

## Rules
- We build step by step. Only do what the current step asks; don't add future features.
- Keep code simple, readable and commented; this is a portfolio project.
- Secrets go in .env files only, never in code. Keep .env.example files up to date.
- Use type hints in Python and functional components with hooks in React.
- After each change, tell me exactly how to run and test it.
- Never bypass, disable or work around any security or restriction: Windows security
  (Smart App Control, Defender, UAC, firewall), antivirus, file permissions, SSL/TLS
  certificate checks, API rate limits, free-tier limits, or any service's terms of use.
- If something is blocked, stop immediately. Explain what was blocked and why, and
  suggest an allowed alternative. Never change system or security settings yourself.
- Only use official APIs and SDKs. No scraping, no unofficial or reverse-engineered access.
- Never run commands with administrator rights unless I explicitly ask.
- Never put secrets (API keys, passwords, tokens) in code, logs or commits; only in .env files.
- Before installing any new package, tell me what it is and why it is needed.
