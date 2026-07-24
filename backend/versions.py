from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

from database import get_db_connection
from models import VersionCreate, VersionOut, UserOut
from auth import get_current_user
from prompts import _get_owned_prompt_or_404

router = APIRouter()


@router.post("/prompts/{prompt_id}/versions", response_model=VersionOut)
def create_version(
    prompt_id: int,
    version: VersionCreate,
    current_user: UserOut = Depends(get_current_user),
):
    """
    Snapshots the prompt's CURRENT state (title, content, category)
    into prompt_versions. The live prompt row is untouched.
    """
    prompt_row = _get_owned_prompt_or_404(prompt_id, current_user.id)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(version_number) as max_version FROM prompt_versions WHERE prompt_id = ?",
            (prompt_id,),
        )
        result = cursor.fetchone()
        next_version_number = (result["max_version"] or 0) + 1

        now = datetime.utcnow().isoformat()
        cursor.execute(
            """
            INSERT INTO prompt_versions
                (prompt_id, user_id, version_number, title, content, category, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prompt_id, current_user.id, next_version_number,
                prompt_row["title"], prompt_row["content"], prompt_row["category"],
                version.note, now,
            ),
        )
        conn.commit()
        version_id = cursor.lastrowid

    return VersionOut(
        id=version_id,
        prompt_id=prompt_id,
        version_number=next_version_number,
        title=prompt_row["title"],
        content=prompt_row["content"],
        category=prompt_row["category"],
        note=version.note,
        created_at=now,
    )


@router.get("/prompts/{prompt_id}/versions", response_model=list[VersionOut])
def list_versions(prompt_id: int, current_user: UserOut = Depends(get_current_user)):
    _get_owned_prompt_or_404(prompt_id, current_user.id)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM prompt_versions WHERE prompt_id = ? ORDER BY version_number DESC",
            (prompt_id,),
        )
        rows = cursor.fetchall()

    return [
        VersionOut(
            id=row["id"], prompt_id=row["prompt_id"], version_number=row["version_number"],
            title=row["title"], content=row["content"], category=row["category"],
            note=row["note"], created_at=row["created_at"],
        )
        for row in rows
    ]


@router.post("/prompts/{prompt_id}/versions/{version_id}/revert", response_model=VersionOut)
def revert_to_version(
    prompt_id: int, version_id: int, current_user: UserOut = Depends(get_current_user)
):
    """
    Copies a past version's content back onto the LIVE prompt.
    Note this does NOT delete any version history -- reverting is itself
    just another change, and you could save a new version afterward too.
    """
    _get_owned_prompt_or_404(prompt_id, current_user.id)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM prompt_versions WHERE id = ? AND prompt_id = ?",
            (version_id, prompt_id),
        )
        version_row = cursor.fetchone()

        if not version_row:
            raise HTTPException(status_code=404, detail="Version not found")

        now = datetime.utcnow().isoformat()
        cursor.execute(
            """
            UPDATE prompts
            SET title = ?, content = ?, category = ?, updated_at = ?
            WHERE id = ?
            """,
            (version_row["title"], version_row["content"], version_row["category"], now, prompt_id),
        )
        conn.commit()

    return VersionOut(
        id=version_row["id"], prompt_id=prompt_id, version_number=version_row["version_number"],
        title=version_row["title"], content=version_row["content"], category=version_row["category"],
        note=version_row["note"], created_at=version_row["created_at"],
    )


def _get_version_content_or_current(prompt_id: int, version_id, current_content: str, current_title: str):
    """
    Shared helper for A/B testing: resolves a version_id to its saved
    content, or falls back to the live prompt's current content if
    version_id is None.
    """
    if version_id is None:
        return current_content, "Current"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM prompt_versions WHERE id = ? AND prompt_id = ?",
            (version_id, prompt_id),
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found")

    return row["content"], f"v{row['version_number']}"
