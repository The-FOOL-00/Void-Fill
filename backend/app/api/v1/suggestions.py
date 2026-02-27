"""Suggestion endpoints — request and list AI suggestions."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.suggestion_schema import (
    SuggestionListResponse,
    SuggestionRequest,
)
from app.services.suggestion_service import SuggestionService

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


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
