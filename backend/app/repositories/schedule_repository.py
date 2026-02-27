"""Repository for ScheduleBlock database operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule_block import ScheduleBlock


class ScheduleRepository:
    """Encapsulates all database access for the ScheduleBlock model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, block: ScheduleBlock) -> ScheduleBlock:
        """Persist a new ScheduleBlock.

        Args:
            block: A fully populated ScheduleBlock ORM instance.

        Returns:
            The persisted block with server-generated fields populated.
        """
        self._session.add(block)
        await self._session.flush()
        await self._session.refresh(block)
        return block

    async def get_by_id(self, block_id: UUID) -> ScheduleBlock | None:
        """Fetch a single schedule block by primary key.

        Args:
            block_id: UUID of the block.

        Returns:
            The ScheduleBlock if found, otherwise ``None``.
        """
        stmt = select(ScheduleBlock).where(ScheduleBlock.id == block_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> list[ScheduleBlock]:
        """Return all schedule blocks for a user ordered by start time ascending.

        Args:
            user_id: UUID of the owning user.

        Returns:
            List of ScheduleBlock instances.
        """
        stmt = (
            select(ScheduleBlock)
            .where(ScheduleBlock.user_id == user_id)
            .order_by(ScheduleBlock.start_time.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user_and_range(
        self, user_id: UUID, range_start: datetime, range_end: datetime
    ) -> list[ScheduleBlock]:
        """Return schedule blocks within a specific time range.

        Args:
            user_id: UUID of the owning user.
            range_start: Inclusive start of the range.
            range_end: Exclusive end of the range.

        Returns:
            List of ScheduleBlock instances within the range.
        """
        stmt = (
            select(ScheduleBlock)
            .where(
                ScheduleBlock.user_id == user_id,
                ScheduleBlock.start_time >= range_start,
                ScheduleBlock.end_time <= range_end,
            )
            .order_by(ScheduleBlock.start_time.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, block: ScheduleBlock) -> None:
        """Remove a schedule block from the database.

        Args:
            block: The ScheduleBlock ORM instance to delete.
        """
        await self._session.delete(block)
        await self._session.flush()
