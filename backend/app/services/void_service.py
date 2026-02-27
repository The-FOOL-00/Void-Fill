"""Service layer for detecting and returning current void (free) time."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.schedule_repository import ScheduleRepository

logger = get_logger(__name__)


class VoidSlot:
    """Represents a gap in the user's schedule."""

    def __init__(self, start: datetime, end: datetime) -> None:
        self.start = start
        self.end = end
        self.duration_minutes = int((end - start).total_seconds() / 60)

    def to_dict(self) -> dict:
        """Serialize the void slot to a JSON-friendly dictionary."""
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "duration_minutes": self.duration_minutes,
        }


class VoidService:
    """Analyses a user's schedule to find unbooked time slots (voids).

    A "void" is any gap between scheduled blocks within the current day
    that could be used for productive work aligned with the user's goals.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._schedule_repo = ScheduleRepository(session)

    async def get_current_void(self, user_id: UUID) -> dict:
        """Return the current or next available void slot for the user.

        Scans today's schedule blocks and identifies gaps.  Returns the
        first void that starts at or after the current UTC time.

        Args:
            user_id: The authenticated user's UUID.

        Returns:
            A dictionary describing the void slot, or a message if none found.
        """
        now = datetime.now(tz=timezone.utc)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        blocks = await self._schedule_repo.list_by_user_and_range(
            user_id, day_start, day_end
        )

        voids = self._find_voids(blocks, day_start, day_end)

        current_or_next = next(
            (v for v in voids if v.end > now),
            None,
        )

        if current_or_next is None:
            logger.info("no_void_found", user_id=str(user_id))
            return {"void": None, "message": "No available void slots remaining today"}

        logger.info(
            "void_found",
            user_id=str(user_id),
            start=current_or_next.start.isoformat(),
            duration=current_or_next.duration_minutes,
        )
        return {"void": current_or_next.to_dict(), "message": "Void slot available"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_voids(
        blocks: list, day_start: datetime, day_end: datetime
    ) -> list[VoidSlot]:
        """Compute free gaps between sorted schedule blocks.

        Args:
            blocks: Schedule blocks sorted by start_time ascending.
            day_start: Beginning of the analysis window.
            day_end: End of the analysis window.

        Returns:
            List of VoidSlot instances representing free gaps.
        """
        voids: list[VoidSlot] = []
        cursor = day_start

        for block in blocks:
            if block.start_time > cursor:
                voids.append(VoidSlot(start=cursor, end=block.start_time))
            if block.end_time > cursor:
                cursor = block.end_time

        if cursor < day_end:
            voids.append(VoidSlot(start=cursor, end=day_end))

        return voids
