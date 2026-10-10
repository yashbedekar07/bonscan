"""BonScan API entry point.

Run locally with:  uvicorn app.main:app --reload
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load variables from backend/.env (if present) into the environment.
load_dotenv()

# Comma-separated list of origins allowed to call the API (the React dev server by default).
FRONTEND_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app = FastAPI(title="BonScan API", version="0.1.0")

# Allow the frontend to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Simple liveness check used by the frontend to confirm the API is up."""
    return {"status": "ok", "app": "BonScan"}
