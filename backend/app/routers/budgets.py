"""Monthly budgets per category.

The user's own Supabase client is used, so Row Level Security makes sure
users can only read and change their own budgets.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from pydantic import BaseModel, Field
from supabase import Client

from app import analytics, data
from app.auth import CurrentUser, get_current_user, get_user_db
from app.routers.analytics import MonthParam
from app.services.forecast import project_month_end
from app.services.insights import budget_status

router = APIRouter(prefix="/api/budgets", tags=["budgets"])

CategoryId = Annotated[int, Path(ge=1, description="Category id (see /api/categories)")]


class Budget(BaseModel):
    category_id: int
    category_name: str
    icon: str | None
    monthly_limit: float


class BudgetIn(BaseModel):
    monthly_limit: float = Field(gt=0, le=100_000, description="Monthly limit in EUR, must be > 0")


class BudgetProgress(Budget):
    month: str
    spent: float
    percent: float  # spent / limit * 100
    status: str  # "ok" (< 80 %), "warning" (80–100 %), "over" (> 100 %)
    projected: float | None  # end-of-month projection, only for the current month


def _to_budget(row: dict) -> Budget:
    category = row.get("categories") or {}
    return Budget(
        category_id=row["category_id"],
        category_name=category.get("name") or "Unknown",
        icon=category.get("icon"),
        monthly_limit=row["monthly_limit"],
    )


@router.get("")
def list_budgets(db: Client = Depends(get_user_db)) -> list[Budget]:
    """All of the user's budgets."""
    return [_to_budget(row) for row in data.budgets(db)]


@router.put("/{category_id}")
def set_budget(
    category_id: CategoryId,
    budget: BudgetIn,
    user: CurrentUser = Depends(get_current_user),
    db: Client = Depends(get_user_db),
) -> Budget:
    """Set or update the monthly limit for one category."""
    category = db.table("categories").select("id, name, icon").eq("id", category_id).limit(1).execute().data
    if not category:
        raise HTTPException(404, "Category not found.")

    # One budget per user and category (unique constraint), so insert-or-update.
    db.table("budgets").upsert(
        {"user_id": user.id, "category_id": category_id, "monthly_limit": round(budget.monthly_limit, 2)},
        on_conflict="user_id,category_id",
    ).execute()

    return Budget(
        category_id=category_id,
        category_name=category[0]["name"],
        icon=category[0]["icon"],
        monthly_limit=round(budget.monthly_limit, 2),
    )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(category_id: CategoryId, db: Client = Depends(get_user_db)) -> Response:
    """Remove the budget for one category (does nothing if there is none)."""
    db.table("budgets").delete().eq("category_id", category_id).execute()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/progress")
def budget_progress(month: MonthParam = None, db: Client = Depends(get_user_db)) -> list[BudgetProgress]:
    """Spent vs limit for every budgeted category in a month (default: current month)."""
    current = analytics.current_month()
    month = month or current
    budgets = [_to_budget(row) for row in data.budgets(db)]
    if not budgets:
        return []

    spent_by_category = analytics.category_totals(data.items_between(db, month, month))
    today = date.today()

    progress = []
    for b in budgets:
        spent = max(spent_by_category.get(b.category_name, 0.0), 0.0)  # deposit returns can't make it negative
        percent, state = budget_status(spent, b.monthly_limit)
        progress.append(BudgetProgress(
            **b.model_dump(),
            month=month,
            spent=spent,
            percent=percent,
            status=state,
            projected=project_month_end(spent, today) if month == current else None,
        ))
    return sorted(progress, key=lambda p: p.percent, reverse=True)
