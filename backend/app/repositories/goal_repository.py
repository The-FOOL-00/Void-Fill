"""Repository for Goal database operations."""

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal


class GoalRepository:
    """Encapsulates all database access for the Goal model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, goal: Goal) -> Goal:
        """Persist a new Goal to the database.

        Args:
            goal: A fully populated Goal ORM instance.

        Returns:
            The persisted Goal with server-generated fields populated.
        """
        self._session.add(goal)
        await self._session.flush()
        await self._session.refresh(goal)
        return goal

    async def get_by_id(self, goal_id: UUID) -> Goal | None:
        """Fetch a single goal by primary key.

        Args:
            goal_id: UUID of the goal.

        Returns:
            The Goal if found, otherwise ``None``.
        """
        stmt = select(Goal).where(Goal.id == goal_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> list[Goal]:
        """Return all goals belonging to a user, ordered by priority descending.

        Args:
            user_id: UUID of the owning user.

        Returns:
            List of Goal instances.
        """
        stmt = (
            select(Goal)
            .where(Goal.user_id == user_id)
            .order_by(Goal.priority.desc(), Goal.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_embedding(
        self,
        user_id: UUID,
        embedding: List[float],
        limit: int = 5,
    ) -> list[Goal]:
        """Find the closest goals using pgvector cosine distance.

        Args:
            user_id: UUID of the owning user.
            embedding: The query embedding vector (384 dimensions).
            limit: Maximum number of results to return.

        Returns:
            List of Goal instances ordered by cosine similarity (closest first).
        """
        stmt = (
            select(Goal)
            .where(Goal.user_id == user_id)
            .where(Goal.embedding.isnot(None))
            .order_by(Goal.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, goal: Goal) -> None:
        """Remove a goal from the database.

        Args:
            goal: The Goal ORM instance to delete.
        """
        await self._session.delete(goal)
        await self._session.flush()
