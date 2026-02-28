"""Habit Engine endpoints — deterministic habit detection from memory."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.habit_schema import HabitSummaryResponse
from app.services.habit_service import HabitService

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get(
    "/summary",
    response_model=HabitSummaryResponse,
    summary="Get habit summary from memory data",
)
async def get_habit_summary(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Detect habits, time patterns, and average session length.

    All detection is deterministic — no LLM calls.
    """
    service = HabitService(db)
    return await service.get_summary(user_id)
