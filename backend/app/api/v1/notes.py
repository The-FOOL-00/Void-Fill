"""Notes endpoints — list user notes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.note_repository import NoteRepository
from app.schemas.note_schema import NoteListResponse, NoteResponse

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get(
    "",
    response_model=NoteListResponse,
    summary="List all notes for the current user",
)
async def list_notes(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteListResponse:
    """Return every note belonging to the authenticated user, newest first."""
    repo = NoteRepository(db)
    notes = await repo.get_notes_for_user(user_id)
    items = [NoteResponse.model_validate(n) for n in notes]
    return NoteListResponse(notes=items, count=len(items))
