from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

from database import get_db_connection
from models import PromptCreate, PromptUpdate, PromptOut, UserOut
from auth import get_current_user

router = APIRouter()


@router.post("/prompts", response_model=PromptOut)
def create_prompt(prompt: PromptCreate, current_user: UserOut = Depends(get_current_user)):
    now = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO prompts (user_id, title, content, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (current_user.id, prompt.title, prompt.content, prompt.category, now, now),
        )
        conn.commit()
        new_id = cursor.lastrowid

    return PromptOut(
        id=new_id,
        title=prompt.title,
        content=prompt.content,
        category=prompt.category,
        created_at=now,
        updated_at=now,
    )


@router.get("/prompts", response_model=list[PromptOut])
def list_prompts(current_user: UserOut = Depends(get_current_user)):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM prompts WHERE user_id = ? ORDER BY updated_at DESC",
            (current_user.id,),
        )
        rows = cursor.fetchall()

    return [
        PromptOut(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            category=row["category"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.get("/prompts/{prompt_id}", response_model=PromptOut)
def get_prompt(prompt_id: int, current_user: UserOut = Depends(get_current_user)):
    row = _get_owned_prompt_or_404(prompt_id, current_user.id)
    return PromptOut(
        id=row["id"],
        title=row["title"],
        content=row["content"],
        category=row["category"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.put("/prompts/{prompt_id}", response_model=PromptOut)
def update_prompt(prompt_id: int, updates: PromptUpdate, current_user: UserOut = Depends(get_current_user)):
    row = _get_owned_prompt_or_404(prompt_id, current_user.id)

    new_title = updates.title if updates.title is not None else row["title"]
    new_content = updates.content if updates.content is not None else row["content"]
    new_category = updates.category if updates.category is not None else row["category"]
    now = datetime.utcnow().isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE prompts
            SET title = ?, content = ?, category = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_title, new_content, new_category, now, prompt_id),
        )
        conn.commit()

    return PromptOut(
        id=prompt_id,
        title=new_title,
        content=new_content,
        category=new_category,
        created_at=row["created_at"],
        updated_at=now,
    )


@router.delete("/prompts/{prompt_id}")
def delete_prompt(prompt_id: int, current_user: UserOut = Depends(get_current_user)):
    _get_owned_prompt_or_404(prompt_id, current_user.id)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        conn.commit()

    return {"message": "Prompt deleted successfully"}


def _get_owned_prompt_or_404(prompt_id: int, user_id: int):
    """
    Shared helper: fetches a prompt and verifies it belongs to the
    requesting user. Raises 404 if it doesn't exist OR belongs to
    someone else -- we deliberately don't distinguish between the two,
    so users can't probe which prompt IDs exist.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM prompts WHERE id = ? AND user_id = ?",
            (prompt_id, user_id),
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return row
