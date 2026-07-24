from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ---------- Auth schemas ----------

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str


# ---------- Prompt schemas ----------

class PromptCreate(BaseModel):
    title: str
    content: str
    category: Optional[str] = "General"


class PromptUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None


class PromptOut(BaseModel):
    id: int
    title: str
    content: str
    category: str
    created_at: str
    updated_at: str


# ---------- Execution schemas ----------

class ExecuteRequest(BaseModel):
    test_input: str
    model: Optional[str] = None


class ExecutionOut(BaseModel):
    id: int
    prompt_id: int
    test_input: str
    response: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_seconds: float
    created_at: str


# ---------- Version schemas ----------

class VersionCreate(BaseModel):
    note: Optional[str] = None


class VersionOut(BaseModel):
    id: int
    prompt_id: int
    version_number: int
    title: str
    content: str
    category: str
    note: Optional[str] = None
    created_at: str


# ---------- A/B comparison schemas ----------

class CompareRequest(BaseModel):
    test_input: str
    version_a_id: Optional[int] = None  # None = use the live/current prompt
    version_b_id: Optional[int] = None  # None = use the live/current prompt
    model: Optional[str] = None


class CompareResult(BaseModel):
    label: str
    content_used: str
    response: str
    model: str
    total_tokens: int
    latency_seconds: float


class CompareResponse(BaseModel):
    result_a: CompareResult
    result_b: CompareResult


# ---------- Analytics schemas ----------

class AnalyticsSummary(BaseModel):
    prompt_id: int
    total_runs: int
    avg_tokens: float
    avg_latency: float
    last_run_at: Optional[str] = None


# ---------- Cost & global dashboard schemas ----------

class CostBreakdown(BaseModel):
    prompt_id: int
    total_cost_usd: float
    total_runs: int


class GlobalStats(BaseModel):
    total_prompts: int
    total_runs: int
    total_tokens: int
    total_cost_usd: float


class CostOverTimePoint(BaseModel):
    date: str
    cost_usd: float


class CategoryUsagePoint(BaseModel):
    category: str
    total_tokens: int


class InsightsResponse(BaseModel):
    global_stats: GlobalStats
    cost_over_time: list[CostOverTimePoint]
    category_usage: list[CategoryUsagePoint]
