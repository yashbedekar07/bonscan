"""App settings, read once from environment variables (backend/.env)."""

import os

from dotenv import load_dotenv

# Load variables from backend/.env (if present) into the environment.
load_dotenv()

# Comma-separated list of origins allowed to call the API (the React dev server by default).
FRONTEND_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

# Supabase project settings. The service key bypasses Row Level Security,
# so it must only ever live on the server, never in the frontend.
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
