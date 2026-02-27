"""Service layer for Goal business logic."""

from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.goal import Goal
from app.repositories.goal_repository import GoalRepository
from app.schemas.goal_schema import (
    GoalCreate,
    GoalListResponse,
    GoalResponse,
    GoalSearchRequest,
    GoalSearchResult,
)
from app.services.embedding_service import get_embedding_service

logger = get_logger(__name__)


class GoalService:
    """Orchestrates goal creation, retrieval, semantic search, and embedding generation."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = GoalRepository(session)
        self._embedding = get_embedding_service()

    async def create_goal(self, user_id: UUID, payload: GoalCreate) -> GoalResponse:
        """Create a new goal and compute its semantic embedding.

        The embedding is generated from the goal title using
        sentence-transformers and stored via pgvector for later
        similarity search.

        Args:
            user_id: The authenticated user's UUID.
            payload: Validated goal creation data.

        Returns:
            The newly created goal as a response schema.
        """
        embedding = await self._embedding.generate_embedding(payload.title)

        goal = Goal(
            user_id=user_id,
            title=payload.title,
            priority=payload.priority,
            embedding=embedding,
        )
        goal = await self._repo.create(goal)

        logger.info("goal_created", goal_id=str(goal.id), user_id=str(user_id))
        return GoalResponse.model_validate(goal)

    async def list_goals(self, user_id: UUID) -> GoalListResponse:
        """Return all goals for the given user.

        Args:
            user_id: The authenticated user's UUID.

        Returns:
            A list wrapper with count.
        """
        goals = await self._repo.list_by_user(user_id)
        items = [GoalResponse.model_validate(g) for g in goals]
        return GoalListResponse(goals=items, count=len(items))

    async def get_goal(self, user_id: UUID, goal_id: UUID) -> GoalResponse:
        """Retrieve a single goal by id, ensuring ownership.

        Args:
            user_id: The authenticated user's UUID.
            goal_id: The UUID of the goal.

        Returns:
            The goal response.

        Raises:
            NotFoundError: If the goal does not exist or does not belong to the user.
        """
        goal = await self._repo.get_by_id(goal_id)
        if goal is None or goal.user_id != user_id:
            raise NotFoundError("Goal", goal_id)
        return GoalResponse.model_validate(goal)

    async def search_goals_by_text(
        self,
        user_id: UUID,
        query: str,
        limit: int = 5,
    ) -> List[GoalSearchResult]:
        """Find goals semantically similar to a natural-language query.

        Flow:
          1. Generate an embedding for the query text.
          2. Run a pgvector cosine-similarity search.
          3. Return the closest goals.

        Args:
            user_id: The authenticated user's UUID.
            query: Free-text search query.
            limit: Maximum number of results (1–20).

        Returns:
            A list of GoalSearchResult ordered by similarity.
        """
        query_embedding = await self._embedding.generate_embedding(query)

        goals = await self._repo.search_by_embedding(
            user_id=user_id,
            embedding=query_embedding,
            limit=limit,
        )

        results = [
            GoalSearchResult(
                goal_id=g.id,
                title=g.title,
                priority=g.priority,
            )
            for g in goals
        ]

        logger.info(
            "goal_search_executed",
            user_id=str(user_id),
            query=query,
            results_count=len(results),
        )
        return results
