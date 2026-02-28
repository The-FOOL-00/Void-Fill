"""Autonomy Engine endpoint — manual trigger."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.autonomy_schema import AutonomyResponse
from app.services.autonomy_service import AutonomyService

router = APIRouter(prefix="/autonomy", tags=["autonomy"])


@router.post(
    "/run",
    response_model=AutonomyResponse,
    summary="Run the autonomy engine once",
)
async def run_autonomy(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger one autonomy cycle.

    Detects the current void slot, picks the best suggestion,
    creates a schedule block, and records the action in memory.
    Deterministic — no AI calls.
    """
    service = AutonomyService(db)
    return await service.run_autonomy(user_id)
