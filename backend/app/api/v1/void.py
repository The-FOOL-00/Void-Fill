"""Void endpoint — find current unbooked time slots."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.void_service import VoidService

router = APIRouter(prefix="/void", tags=["void"])


@router.get(
    "/current",
    summary="Get the current or next available void slot",
)
async def get_current_void(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Analyse today's schedule and return the first available free time slot.

    A "void" is a gap between scheduled blocks that can be filled with
    productive work aligned with the user's goals.
    """
    service = VoidService(db)
    return await service.get_current_void(user_id)
