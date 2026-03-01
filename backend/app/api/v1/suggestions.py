"""Suggestion endpoints — request and list AI suggestions."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.suggestion import Suggestion
from app.schemas.suggestion_schema import (
    SuggestionListResponse,
    SuggestionRequest,
)
from app.services.suggestion_service import SuggestionService

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


class _StatusResponse(BaseModel):
    status: str


@router.post(
    "/request",
    response_model=SuggestionListResponse,
    status_code=201,
    summary="Request new AI suggestions",
)
async def request_suggestions(
    payload: SuggestionRequest,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuggestionListResponse:
    """Generate and persist new AI suggestions for the user.

    Optionally scope to a specific goal by providing ``goal_id``.
    """
    service = SuggestionService(db)
    return await service.request_suggestions(user_id, payload)


@router.post(
    "/{suggestion_id}/accept",
    response_model=_StatusResponse,
    summary="Mark a suggestion as accepted",
)
async def accept_suggestion(
    suggestion_id: UUID,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> _StatusResponse:
    result = await db.execute(
        select(Suggestion).where(
            Suggestion.id == suggestion_id,
            Suggestion.user_id == user_id,
        )
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Suggestion not found")
    suggestion.accepted = True
    await db.commit()
    return _StatusResponse(status="accepted")


@router.post(
    "/skip",
    response_model=_StatusResponse,
    summary="Skip (dismiss) a list of suggestions",
)
async def skip_suggestions(
    suggestion_ids: list[UUID],
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> _StatusResponse:
    """Mark the given suggestions as skipped so they are not shown again."""
    if suggestion_ids:
        result = await db.execute(
            select(Suggestion).where(
                Suggestion.id.in_(suggestion_ids),
                Suggestion.user_id == user_id,
            )
        )
        suggestions = result.scalars().all()
        for s in suggestions:
            s.skipped = True
        await db.commit()
    return _StatusResponse(status="skipped")
