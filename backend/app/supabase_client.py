"""Supabase clients for the backend.

- get_supabase(): a shared client with the public anon key. Only used to
  verify login tokens (see app/auth.py).
- user_client(token): a client that acts AS the logged-in user. All database
  and storage access goes through this, so Row Level Security decides what the
  user may see and change, exactly like in the frontend.
"""

from functools import lru_cache

from supabase import Client, ClientOptions, create_client

from app.config import SUPABASE_ANON_KEY, SUPABASE_URL, ConfigError, supabase_configured


def _check_config() -> None:
    if not supabase_configured():
        raise ConfigError("Supabase is not configured: set SUPABASE_URL and SUPABASE_ANON_KEY in backend/.env.")


@lru_cache
def get_supabase() -> Client:
    """Shared anon client, created on first use (so /api/health works without config)."""
    _check_config()
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def user_client(access_token: str) -> Client:
    """A Supabase client that sends the user's own access token with every request."""
    _check_config()
    return create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY,
        options=ClientOptions(
            headers={"Authorization": f"Bearer {access_token}"},
            # This client lives for one request; it never logs in or refreshes itself.
            auto_refresh_token=False,
            persist_session=False,
        ),
    )
