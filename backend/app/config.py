"""App settings, read once from environment variables (backend/.env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env, no matter which folder the app or a script is started from.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class ConfigError(Exception):
    """A required setting is missing from backend/.env (returned to the client as 503)."""


# Comma-separated list of website origins allowed to call the API (CORS), e.g.
# "http://localhost:5173" locally or "https://bonscan.vercel.app" in production.
# No default on purpose: without it, browsers can't call the API from any site.
# A trailing "/" is removed, because browsers send origins without one.
FRONTEND_ORIGINS: list[str] = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]

# Supabase project settings. We only need the public anon/publishable key:
# every database and storage request is made with the logged-in user's token,
# so Row Level Security always applies.
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "").strip()

# Name of the private storage bucket for receipt photos (created in supabase/schema.sql).
RECEIPTS_BUCKET = "receipts"

# Gemini (Google AI Studio) settings for receipt extraction.
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "").strip() or "gemini-flash-latest"
GEMINI_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "") or "60")

# Fair use of our Gemini quota: receipt scans allowed per user per day (Europe/Berlin day).
SCAN_LIMIT_PER_DAY: int = max(1, int(os.getenv("SCAN_LIMIT_PER_DAY", "") or "15"))


def supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)


def gemini_configured() -> bool:
    return bool(GEMINI_API_KEY)
