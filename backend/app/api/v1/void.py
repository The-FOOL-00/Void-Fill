"""Void Intelligence Engine endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.void_schema import VoidNowResponse
from app.services.void_service import VoidService

router = APIRouter(prefix="/void", tags=["void"])


@router.get(
    "/now",
    response_model=VoidNowResponse,
    summary="Get current void/schedule status with suggestions",
)
async def get_void_now(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Detect whether the user is in a void slot or a scheduled block.

    Returns the current schedule status, void slot details (if any),
    and up to 5 goal-aligned suggestions.  All detection is deterministic
    — no LLM calls are made.
    """
    service = VoidService(db)
    return await service.get_void_status(user_id)
