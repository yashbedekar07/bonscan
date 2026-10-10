"""Helpers for the shared spending categories."""

from typing import Any

from supabase import Client

# Used when the AI (or a user) picks a category that doesn't exist.
FALLBACK_CATEGORY = "Other"


def fetch_categories(db: Client) -> list[dict[str, Any]]:
    """Return all categories as dicts with id, name and icon, ordered by id."""
    return db.table("categories").select("id, name, icon").order("id").execute().data


def category_ids_by_name(db: Client) -> dict[str, int]:
    """Map each category name to its id, e.g. {"Groceries": 1, ...}."""
    return {row["name"]: row["id"] for row in fetch_categories(db)}
