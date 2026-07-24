import asyncio
import time
from fastapi import APIRouter, Depends

from models import CompareRequest, CompareResponse, CompareResult, UserOut
from auth import get_current_user
from prompts import _get_owned_prompt_or_404
from versions import _get_version_content_or_current
from execution import call_groq, DEFAULT_MODEL

router = APIRouter()


async def _run_single(label: str, system_prompt: str, test_input: str, model: str) -> CompareResult:
    start = time.time()
    result = await call_groq(system_prompt, test_input, model)
    elapsed = round(time.time() - start, 2)

    response_text = result["choices"][0]["message"]["content"]
    usage = result.get("usage", {})
    total_tokens = usage.get("total_tokens", 0)

    return CompareResult(
        label=label,
        content_used=system_prompt,
        response=response_text,
        model=model,
        total_tokens=total_tokens,
        latency_seconds=elapsed,
    )


@router.post("/prompts/{prompt_id}/compare", response_model=CompareResponse)
async def compare_versions(
    prompt_id: int,
    request: CompareRequest,
    current_user: UserOut = Depends(get_current_user),
):
    prompt_row = _get_owned_prompt_or_404(prompt_id, current_user.id)
    model = request.model or DEFAULT_MODEL

    content_a, label_a = _get_version_content_or_current(
        prompt_id, request.version_a_id, prompt_row["content"], prompt_row["title"]
    )
    content_b, label_b = _get_version_content_or_current(
        prompt_id, request.version_b_id, prompt_row["content"], prompt_row["title"]
    )

    # Run both Groq calls CONCURRENTLY -- total wait time is roughly the
    # slower of the two calls, not the sum of both.
    result_a, result_b = await asyncio.gather(
        _run_single(label_a, content_a, request.test_input, model),
        _run_single(label_b, content_b, request.test_input, model),
    )

    return CompareResponse(result_a=result_a, result_b=result_b)
