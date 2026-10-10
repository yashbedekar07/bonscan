"""BonScan API entry point.

Run locally with:  uvicorn app.main:app --reload
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user
from app.config import FRONTEND_ORIGINS
from app.supabase_client import get_supabase

app = FastAPI(title="BonScan API", version="0.2.0")

# Allow the frontend to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Response models (also shown in the /docs page) ----------


class MeResponse(BaseModel):
    id: str
    email: str | None


class Category(BaseModel):
    id: int
    name: str
    icon: str | None


# ---------- Endpoints ----------


@app.get("/api/health")
def health() -> dict[str, str]:
    """Simple liveness check used by the frontend to confirm the API is up."""
    return {"status": "ok", "app": "BonScan"}


@app.get("/api/me")
def me(user: CurrentUser = Depends(get_current_user)) -> MeResponse:
    """Return the logged-in user's id and email."""
    return MeResponse(id=user.id, email=user.email)


@app.get("/api/categories")
def list_categories(_user: CurrentUser = Depends(get_current_user)) -> list[Category]:
    """Return all spending categories (shared by every user)."""
    result = (
        get_supabase()
        .table("categories")
        .select("id, name, icon")
        .order("id")
        .execute()
    )
    return [Category(**row) for row in result.data]
