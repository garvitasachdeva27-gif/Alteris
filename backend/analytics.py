from fastapi import APIRouter, Depends

from database import get_db_connection
from models import (
    AnalyticsSummary, UserOut, InsightsResponse, GlobalStats,
    CostOverTimePoint, CategoryUsagePoint,
)
from auth import get_current_user
from prompts import _get_owned_prompt_or_404

router = APIRouter()

# Groq pricing in USD per 1 million tokens.
# NOTE: these are illustrative rates for this project -- check console.groq.com/pricing
# for current figures before relying on this for real budgeting.
MODEL_PRICING = {
    "openai/gpt-oss-20b": {"input": 0.05, "output": 0.08},
    "openai/gpt-oss-120b": {"input": 0.59, "output": 0.79},
}
DEFAULT_PRICING = {"input": 0.10, "output": 0.10}  # fallback for unlisted models


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
    cost = (
        (prompt_tokens / 1_000_000) * pricing["input"]
        + (completion_tokens / 1_000_000) * pricing["output"]
    )
    return round(cost, 6)


@router.get("/prompts/{prompt_id}/analytics", response_model=AnalyticsSummary)
def get_prompt_analytics(prompt_id: int, current_user: UserOut = Depends(get_current_user)):
    _get_owned_prompt_or_404(prompt_id, current_user.id)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_runs,
                AVG(total_tokens) as avg_tokens,
                AVG(latency_seconds) as avg_latency,
                MAX(created_at) as last_run_at
            FROM executions
            WHERE prompt_id = ?
            """,
            (prompt_id,),
        )
        row = cursor.fetchone()

    return AnalyticsSummary(
        prompt_id=prompt_id,
        total_runs=row["total_runs"] or 0,
        avg_tokens=round(row["avg_tokens"], 1) if row["avg_tokens"] else 0.0,
        avg_latency=round(row["avg_latency"], 2) if row["avg_latency"] else 0.0,
        last_run_at=row["last_run_at"],
    )


@router.get("/insights", response_model=InsightsResponse)
def get_insights(current_user: UserOut = Depends(get_current_user)):
    """
    Global dashboard data: totals across ALL of this user's prompts,
    a cost-over-time series, and token usage grouped by category.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Every execution row for this user, joined with the prompt's
        # category (needed for the category breakdown chart).
        cursor.execute(
            """
            SELECT e.model, e.prompt_tokens, e.completion_tokens, e.total_tokens,
                   e.created_at, p.category
            FROM executions e
            JOIN prompts p ON e.prompt_id = p.id
            WHERE e.user_id = ?
            """,
            (current_user.id,),
        )
        rows = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) as count FROM prompts WHERE user_id = ?", (current_user.id,))
        total_prompts = cursor.fetchone()["count"]

    total_runs = len(rows)
    total_tokens = sum(r["total_tokens"] for r in rows)
    total_cost = sum(
        estimate_cost(r["model"], r["prompt_tokens"], r["completion_tokens"]) for r in rows
    )

    # Cost grouped by day (YYYY-MM-DD) for the line chart.
    cost_by_day = {}
    for r in rows:
        day = r["created_at"][:10]  # ISO string -> just the date part
        cost_by_day[day] = cost_by_day.get(day, 0) + estimate_cost(
            r["model"], r["prompt_tokens"], r["completion_tokens"]
        )
    cost_over_time = [
        CostOverTimePoint(date=day, cost_usd=round(cost, 6))
        for day, cost in sorted(cost_by_day.items())
    ]

    # Tokens grouped by category for the bar chart.
    tokens_by_category = {}
    for r in rows:
        cat = r["category"] or "General"
        tokens_by_category[cat] = tokens_by_category.get(cat, 0) + r["total_tokens"]
    category_usage = [
        CategoryUsagePoint(category=cat, total_tokens=tokens)
        for cat, tokens in sorted(tokens_by_category.items(), key=lambda x: -x[1])
    ]

    return InsightsResponse(
        global_stats=GlobalStats(
            total_prompts=total_prompts,
            total_runs=total_runs,
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 4),
        ),
        cost_over_time=cost_over_time,
        category_usage=category_usage,
    )
