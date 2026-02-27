"""Service layer for AI suggestion generation."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.suggestion import Suggestion
from app.repositories.goal_repository import GoalRepository
from app.repositories.suggestion_repository import SuggestionRepository
from app.schemas.suggestion_schema import (
    SuggestionListResponse,
    SuggestionRequest,
    SuggestionResponse,
)

logger = get_logger(__name__)


class SuggestionService:
    """Generates and retrieves AI-powered suggestions for a user."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = SuggestionRepository(session)
        self._goal_repo = GoalRepository(session)

    async def request_suggestions(
        self, user_id: UUID, payload: SuggestionRequest
    ) -> SuggestionListResponse:
        """Generate new suggestions for the user.

        When a ``goal_id`` is provided the suggestions are scoped to that
        goal.  Otherwise they are general productivity recommendations.

        The LLM parsing service will replace the placeholder generation
        logic below.

        Args:
            user_id: The authenticated user's UUID.
            payload: Request parameters including optional goal_id and limit.

        Returns:
            A list of newly created suggestions.
        """
        goal_title: Optional[str] = None
        if payload.goal_id is not None:
            goal = await self._goal_repo.get_by_id(payload.goal_id)
            if goal is not None and goal.user_id == user_id:
                goal_title = goal.title

        generated = self._generate(
            user_id=user_id,
            goal_id=payload.goal_id,
            goal_title=goal_title,
            limit=payload.limit,
        )

        persisted = await self._repo.create_many(generated)

        items = [SuggestionResponse.model_validate(s) for s in persisted]
        logger.info(
            "suggestions_generated",
            user_id=str(user_id),
            count=len(items),
            goal_id=str(payload.goal_id) if payload.goal_id else None,
        )
        return SuggestionListResponse(suggestions=items, count=len(items))

    async def list_suggestions(
        self, user_id: UUID, goal_id: Optional[UUID] = None, limit: int = 20
    ) -> SuggestionListResponse:
        """Retrieve existing suggestions for the user.

        Args:
            user_id: The authenticated user's UUID.
            goal_id: Optional goal filter.
            limit: Maximum results.

        Returns:
            A list wrapper with count.
        """
        suggestions = await self._repo.list_by_user(user_id, goal_id=goal_id, limit=limit)
        items = [SuggestionResponse.model_validate(s) for s in suggestions]
        return SuggestionListResponse(suggestions=items, count=len(items))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate(
        user_id: UUID,
        goal_id: Optional[UUID],
        goal_title: Optional[str],
        limit: int,
    ) -> list[Suggestion]:
        """Create placeholder suggestion ORM instances.

        The LLM module will replace this with real generation logic.

        Args:
            user_id: User UUID.
            goal_id: Optional goal UUID.
            goal_title: Optional goal title for context.
            limit: Number of suggestions to produce.

        Returns:
            List of unsaved Suggestion ORM instances.
        """
        suggestions: list[Suggestion] = []
        context = f" for goal '{goal_title}'" if goal_title else ""

        for idx in range(limit):
            score = round(1.0 - (idx * 0.1), 2)
            suggestions.append(
                Suggestion(
                    user_id=user_id,
                    goal_id=goal_id,
                    text=f"Suggestion {idx + 1}{context}: optimise your next void slot",
                    score=max(score, 0.1),
                    accepted=False,
                )
            )
        return suggestions
