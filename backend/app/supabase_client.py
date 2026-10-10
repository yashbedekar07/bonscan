"""Shared Supabase client for the backend."""

from functools import lru_cache

from supabase import Client, create_client

from app.config import SUPABASE_SERVICE_KEY, SUPABASE_URL


@lru_cache
def get_supabase() -> Client:
    """Create the Supabase client on first use and reuse it afterwards.

    Created lazily so the app (and /api/health) still starts when Supabase
    isn't configured yet; only endpoints that need Supabase will fail.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env"
        )
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
