"""Repository for Memory database operations — pure SQL, no AI."""

import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory


class MemoryRepository:
    """Encapsulates all database access for the Memory model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_memory(
        self,
        user_id: UUID,
        goal_id: Optional[UUID],
        title: str,
        minutes: int,
    ) -> Memory:
        """Insert a new memory record.

        Args:
            user_id: Owner of the memory.
            goal_id: Optional associated goal.
            title: Human-readable action title.
            minutes: Duration in minutes.

        Returns:
            The persisted Memory instance.
        """
        memory = Memory(
            id=uuid.uuid4(),
            user_id=user_id,
            goal_id=goal_id,
            title=title,
            minutes=minutes,
        )
        self._session.add(memory)
        await self._session.commit()
        await self._session.refresh(memory)
        return memory

    async def list_top_goals(
        self,
        user_id: UUID,
        limit: int = 5,
    ) -> list[dict]:
        """Return the top goals by total minutes spent.

        Groups by (goal_id, title) and orders by total_minutes DESC.

        Args:
            user_id: Owner of the memories.
            limit: Maximum number of results.

        Returns:
            List of dicts with goal_id, title, sessions, total_minutes.
        """
        stmt = (
            select(
                Memory.goal_id,
                Memory.title,
                func.count().label("sessions"),
                func.sum(Memory.minutes).label("total_minutes"),
            )
            .where(Memory.user_id == user_id)
            .group_by(Memory.goal_id, Memory.title)
            .order_by(func.sum(Memory.minutes).desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        return [
            {
                "goal_id": row.goal_id,
                "title": row.title,
                "sessions": row.sessions,
                "total_minutes": row.total_minutes,
            }
            for row in rows
        ]

    async def list_recent_actions(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[dict]:
        """Return the most recent actions, newest first.

        Args:
            user_id: Owner of the memories.
            limit: Maximum number of results.

        Returns:
            List of dicts with title, minutes, created_at.
        """
        stmt = (
            select(Memory)
            .where(Memory.user_id == user_id)
            .order_by(Memory.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "title": row.title,
                "minutes": row.minutes,
                "created_at": row.created_at,
            }
            for row in rows
        ]
