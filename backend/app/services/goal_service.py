"""Service layer for Goal business logic."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.goal import Goal
from app.repositories.goal_repository import GoalRepository
from app.schemas.goal_schema import GoalCreate, GoalListResponse, GoalResponse

logger = get_logger(__name__)


class GoalService:
    """Orchestrates goal creation, retrieval, and embedding generation."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = GoalRepository(session)

    async def create_goal(self, user_id: UUID, payload: GoalCreate) -> GoalResponse:
        """Create a new goal and compute its embedding.

        Args:
            user_id: The authenticated user's UUID.
            payload: Validated goal creation data.

        Returns:
            The newly created goal as a response schema.
        """
        embedding = self._compute_embedding(payload.title)

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_embedding(text: str) -> list[float]:
        """Generate a 384-dimensional embedding for the given text.

        This uses a zero-vector placeholder.  The sentence-transformers
        model will be loaded here once the AI module is integrated.

        Args:
            text: The text to embed.

        Returns:
            A list of 384 floats representing the embedding vector.
        """
        # sentence-transformers integration point
        return [0.0] * 384
