"""BonScan API entry point.

Run locally with:  uvicorn app.main:app --reload
Run on Render with: uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""

import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase import Client

from app import receipts
from app.routers import analytics, budgets, export, insights
from app.auth import CurrentUser, get_current_user, get_user_db
from app.categories import fetch_categories
from app.config import FRONTEND_ORIGINS, ConfigError, gemini_configured, supabase_configured
from app.logging_setup import setup_logging
from app.schemas import Category

setup_logging()
logger = logging.getLogger(__name__)

if not FRONTEND_ORIGINS:
    logger.warning("FRONTEND_ORIGINS is empty: browsers won't be allowed to call this API (CORS).")
else:
    logger.info("CORS allowed origins: %s", ", ".join(FRONTEND_ORIGINS))

app = FastAPI(title="BonScan API", version="0.4.0")

# Allow the frontend to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ConfigError)
def config_error_handler(_request: Request, error: ConfigError) -> JSONResponse:
    """Missing settings → a clear 503 the frontend can show, instead of a crash."""
    return JSONResponse(status_code=503, content={"detail": str(error)})


# Receipt endpoints live in app/receipts.py, everything else in app/routers/.
app.include_router(receipts.router)
app.include_router(analytics.router)
app.include_router(budgets.router)
app.include_router(insights.router)
app.include_router(export.router)


class HealthResponse(BaseModel):
    status: str
    app: str
    supabase_configured: bool
    gemini_configured: bool


class MeResponse(BaseModel):
    id: str
    email: str | None


@app.get("/api/health")
def health() -> HealthResponse:
    """Liveness check for the frontend; also says whether backend/.env is complete."""
    return HealthResponse(
        status="ok",
        app="BonScan",
        supabase_configured=supabase_configured(),
        gemini_configured=gemini_configured(),
    )


@app.get("/api/me")
def me(user: CurrentUser = Depends(get_current_user)) -> MeResponse:
    """Return the logged-in user's id and email."""
    return MeResponse(id=user.id, email=user.email)


@app.get("/api/categories")
def list_categories(db: Client = Depends(get_user_db)) -> list[Category]:
    """Return all spending categories (shared by every user)."""
    return [Category(**row) for row in fetch_categories(db)]
