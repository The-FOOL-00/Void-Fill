"""Schedule endpoints — create and list schedule blocks."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.schedule_schema import (
    ScheduleBlockCreate,
    ScheduleBlockListResponse,
    ScheduleBlockResponse,
)
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post(
    "",
    response_model=ScheduleBlockResponse,
    status_code=201,
    summary="Create a schedule block",
)
async def create_schedule_block(
    payload: ScheduleBlockCreate,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScheduleBlockResponse:
    """Add a new time block to the user's schedule."""
    service = ScheduleService(db)
    return await service.create_block(user_id, payload)


@router.get(
    "",
    response_model=ScheduleBlockListResponse,
    summary="List all schedule blocks for the current user",
)
async def list_schedule_blocks(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScheduleBlockListResponse:
    """Return all schedule blocks for the authenticated user ordered chronologically."""
    service = ScheduleService(db)
    return await service.list_blocks(user_id)
