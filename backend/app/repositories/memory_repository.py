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
        await self._session.flush()
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

    async def list_habit_stats(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[dict]:
        """Return goal-level aggregates for habit detection.

        Groups by title and orders by total_minutes DESC.

        Args:
            user_id: Owner of the memories.
            limit: Maximum number of results.

        Returns:
            List of dicts with title, sessions, total_minutes.
        """
        stmt = (
            select(
                Memory.title,
                func.count().label("sessions"),
                func.sum(Memory.minutes).label("total_minutes"),
            )
            .where(Memory.user_id == user_id)
            .group_by(Memory.title)
            .order_by(func.sum(Memory.minutes).desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        return [
            {
                "title": row.title,
                "sessions": row.sessions,
                "total_minutes": row.total_minutes,
            }
            for row in rows
        ]

    async def list_time_patterns(
        self,
        user_id: UUID,
        limit: int = 8,
    ) -> list[dict]:
        """Return hour-of-day session counts for time-pattern detection.

        Args:
            user_id: Owner of the memories.
            limit: Maximum number of hour buckets.

        Returns:
            List of dicts with hour and sessions, ordered by sessions DESC.
        """
        hour_col = func.extract("hour", Memory.created_at).label("hour")
        stmt = (
            select(
                hour_col,
                func.count().label("sessions"),
            )
            .where(Memory.user_id == user_id)
            .group_by(hour_col)
            .order_by(func.count().desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        return [
            {
                "hour": int(row.hour),
                "sessions": row.sessions,
            }
            for row in rows
        ]

    async def average_session_minutes(
        self,
        user_id: UUID,
    ) -> int:
        """Return the average session duration in minutes.

        Args:
            user_id: Owner of the memories.

        Returns:
            Integer average, or 0 if no memories exist.
        """
        stmt = (
            select(func.avg(Memory.minutes))
            .where(Memory.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        avg = result.scalar()
        return int(avg) if avg is not None else 0
