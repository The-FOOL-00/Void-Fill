"""Memory service — records completed actions and returns behavior summaries.

Pure SQL + Python.  No LLM calls, no embeddings.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.memory_repository import MemoryRepository

logger = get_logger(__name__)


class MemoryService:
    """Orchestrates memory recording and retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = MemoryRepository(session)

    async def record_action(
        self,
        user_id: UUID,
        goal_id: Optional[UUID],
        title: str,
        minutes: int,
    ) -> None:
        """Record a completed action in the memory store.

        Args:
            user_id: Owner of the action.
            goal_id: Optional associated goal.
            title: Human-readable action title.
            minutes: Duration in minutes.
        """
        await self._repo.create_memory(
            user_id=user_id,
            goal_id=goal_id,
            title=title,
            minutes=minutes,
        )
        logger.info("memory_recorded", user_id=str(user_id), title=title, minutes=minutes)

    async def get_summary(self, user_id: UUID) -> dict:
        """Return a behavior summary for the user.

        Returns:
            Dict with top_goals and recent_actions lists.
        """
        top_goals = await self._repo.list_top_goals(user_id)
        recent_actions = await self._repo.list_recent_actions(user_id)

        logger.info("memory_summary_requested", user_id=str(user_id))

        return {
            "top_goals": top_goals,
            "recent_actions": recent_actions,
        }
