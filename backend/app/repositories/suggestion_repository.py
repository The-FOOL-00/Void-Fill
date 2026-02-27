"""Repository for Suggestion database operations."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.suggestion import Suggestion


class SuggestionRepository:
    """Encapsulates all database access for the Suggestion model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, suggestion: Suggestion) -> Suggestion:
        """Persist a new Suggestion.

        Args:
            suggestion: A fully populated Suggestion ORM instance.

        Returns:
            The persisted Suggestion with server-generated fields populated.
        """
        self._session.add(suggestion)
        await self._session.flush()
        await self._session.refresh(suggestion)
        return suggestion

    async def create_many(self, suggestions: list[Suggestion]) -> list[Suggestion]:
        """Persist multiple Suggestions in a single flush.

        Args:
            suggestions: List of Suggestion ORM instances.

        Returns:
            The list of persisted Suggestion instances.
        """
        self._session.add_all(suggestions)
        await self._session.flush()
        for s in suggestions:
            await self._session.refresh(s)
        return suggestions

    async def get_by_id(self, suggestion_id: UUID) -> Suggestion | None:
        """Fetch a single suggestion by primary key.

        Args:
            suggestion_id: UUID of the suggestion.

        Returns:
            The Suggestion if found, otherwise ``None``.
        """
        stmt = select(Suggestion).where(Suggestion.id == suggestion_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: UUID,
        goal_id: Optional[UUID] = None,
        limit: int = 20,
    ) -> list[Suggestion]:
        """Return suggestions for a user, optionally filtered by goal.

        Args:
            user_id: UUID of the owning user.
            goal_id: Optional goal UUID to filter by.
            limit: Maximum number of suggestions to return.

        Returns:
            List of Suggestion instances ordered by score descending.
        """
        stmt = (
            select(Suggestion)
            .where(Suggestion.user_id == user_id)
            .order_by(Suggestion.score.desc(), Suggestion.created_at.desc())
            .limit(limit)
        )
        if goal_id is not None:
            stmt = stmt.where(Suggestion.goal_id == goal_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_accepted(self, suggestion: Suggestion) -> Suggestion:
        """Mark a suggestion as accepted by the user.

        Args:
            suggestion: The Suggestion ORM instance to update.

        Returns:
            The updated Suggestion instance.
        """
        suggestion.accepted = True
        await self._session.flush()
        await self._session.refresh(suggestion)
        return suggestion
