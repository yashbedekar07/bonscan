"""Authentication dependencies for protected endpoints.

Usage:
    @app.get("/api/something")
    def something(db: Client = Depends(get_user_db)) -> ...:
        ...  # db acts as the logged-in user (Row Level Security applies)
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from supabase import Client

from app.config import ConfigError
from app.supabase_client import get_supabase, user_client

# Reads the "Authorization: Bearer <token>" header. auto_error=False lets us
# return our own 401 (FastAPI's default for a missing header is 403).
bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """The logged-in user, as verified by Supabase."""

    id: str
    email: str | None
    access_token: str  # used to talk to Supabase on the user's behalf; never logged


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Verify the Supabase access token and return the user, or raise 401."""
    if credentials is None:
        raise _unauthorized("Missing bearer token")

    token = credentials.credentials
    try:
        # Asks Supabase Auth to validate the token. This also rejects tokens
        # of users who have logged out or been deleted.
        response = get_supabase().auth.get_user(token)
    except ConfigError:
        raise  # Supabase not configured: a server problem, not the user's fault
    except Exception:
        raise _unauthorized("Invalid or expired token")

    if response is None or response.user is None:
        raise _unauthorized("Invalid or expired token")

    return CurrentUser(id=response.user.id, email=response.user.email, access_token=token)


def get_user_db(user: CurrentUser = Depends(get_current_user)) -> Client:
    """Supabase client acting as the logged-in user."""
    return user_client(user.access_token)
