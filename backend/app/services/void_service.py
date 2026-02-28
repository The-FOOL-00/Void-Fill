"""Void Intelligence Engine — deterministic scheduler + AI suggestions.

Detects whether the user is currently in a scheduled block or a void
(free-time) slot by querying the schedule with pure SQL + Python logic.
No LLM calls are made in this module.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.suggestion_repository import SuggestionRepository
from app.services.suggestion_service import SuggestionService

logger = get_logger(__name__)


class VoidService:
    """Deterministic void-slot detection and suggestion surfacing.

    A **void** is any gap between scheduled blocks within the next 12 hours
    that could be filled with productive work aligned with the user's goals.

    IMPORTANT: This service is instantiated *per request* — never cached at
    module level — to avoid stale-session bugs.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._schedule_repo = ScheduleRepository(session)
        self._suggestion_repo = SuggestionRepository(session)
        self._suggestion_service = SuggestionService(session)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_void_status(self, user_id: UUID) -> dict:
        """Return the user's current schedule status and void information.

        Steps (all deterministic — no LLM):
        1. Compute ``now`` and a 12-hour look-ahead window.
        2. Fetch overlapping schedule blocks (sorted ASC).
        3. Check if the user is inside a block right now.
        4. If not, compute the void slot until the next block (or 12 h).
        5. Load top suggestions.
        6. Return a plain dict (no ORM objects).

        Args:
            user_id: The authenticated user's UUID.

        Returns:
            A JSON-serialisable dictionary matching ``VoidNowResponse``.
        """
        logger.info("void_status_requested", user_id=str(user_id))

        # Step 1 — explicit UTC time
        now = datetime.now(timezone.utc)
        range_end = now + timedelta(hours=12)

        # Step 2 — load schedule blocks (guaranteed ORDER BY start_time ASC)
        blocks = await self._schedule_repo.list_overlapping_blocks(
            user_id, now, range_end
        )

        # Step 3 — am I inside a block right now?
        current_block = next(
            (b for b in blocks if b.start_time <= now and b.end_time >= now),
            None,
        )

        if current_block is not None:
            logger.info(
                "user_in_scheduled_block",
                user_id=str(user_id),
                block_type=current_block.block_type,
            )
            return {
                "status": "scheduled",
                "current_block": self._block_to_dict(current_block),
                "void_slot": None,
                "suggestions": [],
            }

        # Step 4 — user is in a void; find the next block
        future_blocks = [b for b in blocks if b.start_time > now]
        if future_blocks:
            void_start = now
            void_end = future_blocks[0].start_time
        else:
            void_start = now
            void_end = range_end

        # Step 5 — duration (never negative)
        duration_minutes = max(
            0, int((void_end - void_start).total_seconds() / 60)
        )

        logger.info(
            "void_slot_detected",
            user_id=str(user_id),
            duration_minutes=duration_minutes,
        )

        # Step 6 — load ranked suggestions (empty list if none exist, never null)
        ranked_pairs = await self._suggestion_service.get_ranked_suggestions(
            user_id=user_id,
            void_minutes=duration_minutes,
        )
        suggestion_dicts = [
            {
                "goal_id": str(s.goal_id) if s.goal_id else None,
                "title": s.text,
                "score": round(final_score, 2),
            }
            for final_score, s in ranked_pairs
        ]

        # Step 7 — return plain dict (no ORM objects)
        return {
            "status": "void",
            "current_block": None,
            "void_slot": {
                "start_time": void_start.isoformat(),
                "end_time": void_end.isoformat(),
                "duration_minutes": duration_minutes,
            },
            "suggestions": suggestion_dicts,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _block_to_dict(block) -> dict:
        """Convert a ScheduleBlock ORM instance to a plain dictionary."""
        return {
            "id": str(block.id),
            "user_id": str(block.user_id),
            "start_time": block.start_time.isoformat(),
            "end_time": block.end_time.isoformat(),
            "block_type": block.block_type,
            "created_at": block.created_at.isoformat(),
        }
