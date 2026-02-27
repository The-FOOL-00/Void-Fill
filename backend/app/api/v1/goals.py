"""Goal endpoints — create and list user goals."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.goal_schema import GoalCreate, GoalListResponse, GoalResponse
from app.services.goal_service import GoalService

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post(
    "",
    response_model=GoalResponse,
    status_code=201,
    summary="Create a new goal",
)
async def create_goal(
    payload: GoalCreate,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalResponse:
    """Create a goal with automatic embedding generation for semantic search."""
    service = GoalService(db)
    return await service.create_goal(user_id, payload)


@router.get(
    "",
    response_model=GoalListResponse,
    summary="List all goals for the current user",
)
async def list_goals(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalListResponse:
    """Return all goals belonging to the authenticated user, ordered by priority."""
    service = GoalService(db)
    return await service.list_goals(user_id)
