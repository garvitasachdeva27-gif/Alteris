import os
import time
import httpx
from datetime import datetime
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException

from database import get_db_connection
from models import ExecuteRequest, ExecutionOut, UserOut
from auth import get_current_user
from prompts import _get_owned_prompt_or_404

load_dotenv()

router = APIRouter()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"


async def call_groq(system_prompt: str, user_message: str, model: str = DEFAULT_MODEL) -> dict:
    """
    Sends a system prompt + user message to Groq and returns the raw response.
    This is the ONLY function in the entire app that knows about Groq's API shape.
    If we ever add another provider, everything else stays unchanged.
    """
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is not configured on the server. Check your .env file."
        )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(GROQ_API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Groq API error: {response.text}"
        )

    return response.json()


@router.post("/prompts/{prompt_id}/execute", response_model=ExecutionOut)
async def execute_prompt(
    prompt_id: int,
    request: ExecuteRequest,
    current_user: UserOut = Depends(get_current_user),
):
    # Reuse the ownership check from prompts.py -- one source of truth
    # for "does this prompt exist and belong to this user."
    prompt_row = _get_owned_prompt_or_404(prompt_id, current_user.id)

    start_time = time.time()
    result = await call_groq(
        system_prompt=prompt_row["content"],
        user_message=request.test_input,
        model=request.model or DEFAULT_MODEL,
    )
    elapsed_seconds = round(time.time() - start_time, 2)

    response_text = result["choices"][0]["message"]["content"]
    usage = result.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

    now = datetime.utcnow().isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO executions
                (prompt_id, user_id, test_input, response, model,
                 prompt_tokens, completion_tokens, total_tokens,
                 latency_seconds, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prompt_id, current_user.id, request.test_input, response_text,
                request.model or DEFAULT_MODEL, prompt_tokens, completion_tokens,
                total_tokens, elapsed_seconds, now,
            ),
        )
        conn.commit()
        execution_id = cursor.lastrowid

    return ExecutionOut(
        id=execution_id,
        prompt_id=prompt_id,
        test_input=request.test_input,
        response=response_text,
        model=request.model or DEFAULT_MODEL,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        latency_seconds=elapsed_seconds,
        created_at=now,
    )


@router.get("/prompts/{prompt_id}/history", response_model=list[ExecutionOut])
def get_execution_history(prompt_id: int, current_user: UserOut = Depends(get_current_user)):
    # Confirms ownership before returning any history rows.
    _get_owned_prompt_or_404(prompt_id, current_user.id)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM executions WHERE prompt_id = ? ORDER BY created_at DESC",
            (prompt_id,),
        )
        rows = cursor.fetchall()

    return [
        ExecutionOut(
            id=row["id"],
            prompt_id=row["prompt_id"],
            test_input=row["test_input"],
            response=row["response"],
            model=row["model"],
            prompt_tokens=row["prompt_tokens"],
            completion_tokens=row["completion_tokens"],
            total_tokens=row["total_tokens"],
            latency_seconds=row["latency_seconds"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
