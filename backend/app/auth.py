"""Authentication dependency for protected endpoints.

Usage:
    @app.get("/api/something")
    def something(user: CurrentUser = Depends(get_current_user)) -> ...:
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.supabase_client import get_supabase

# Reads the "Authorization: Bearer <token>" header. auto_error=False lets us
# return our own 401 (FastAPI's default for a missing header is 403).
bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """The logged-in user, as verified by Supabase."""

    id: str
    email: str | None
    access_token: str  # kept so later endpoints can act on the user's behalf


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
    except RuntimeError:
        raise  # Supabase not configured: a server problem, not the user's fault
    except Exception:
        raise _unauthorized("Invalid or expired token")

    if response is None or response.user is None:
        raise _unauthorized("Invalid or expired token")

    return CurrentUser(id=response.user.id, email=response.user.email, access_token=token)
