"""Memory Engine endpoints — record actions and retrieve behavior summaries."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.memory_schema import (
    MemoryRecordRequest,
    MemorySummaryResponse,
)
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get(
    "/summary",
    response_model=MemorySummaryResponse,
    summary="Get behavior memory summary",
)
async def get_memory_summary(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemorySummaryResponse:
    """Return top goals by time invested and recent actions."""
    service = MemoryService(db)
    return await service.get_summary(user_id)


@router.post(
    "",
    status_code=201,
    summary="Record a completed action",
)
async def record_memory(
    payload: MemoryRecordRequest,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Record a completed action in the memory store."""
    service = MemoryService(db)
    await service.record_action(
        user_id=user_id,
        goal_id=payload.goal_id,
        title=payload.title,
        minutes=payload.minutes,
    )
    return {"status": "recorded"}
