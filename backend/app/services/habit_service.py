"""Habit Engine — deterministic pattern learning from memory data.

Detects strong habits, time-of-day patterns, and average session length
using pure SQL + Python math.  No LLM calls, no embeddings.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.memory_repository import MemoryRepository

logger = get_logger(__name__)


class HabitService:
    """Deterministic habit detection from the Memory table.

    IMPORTANT: Instantiate inside request handlers only — never at
    module level.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = MemoryRepository(session)

    async def get_summary(self, user_id: UUID) -> dict:
        """Return a full habit summary for the user.

        Steps:
        1. Load habit stats (grouped by title).
        2. Load time-of-day patterns.
        3. Load average session minutes.
        4. Compute habit_strength for each goal.
        5. Return formatted response.

        Args:
            user_id: The authenticated user's UUID.

        Returns:
            Dict with top_habits, time_patterns, avg_session_minutes.
        """
        logger.info("habit_summary_requested", user_id=str(user_id))

        # Step 1 — load raw stats
        habits = await self._repo.list_habit_stats(user_id)
        patterns = await self._repo.list_time_patterns(user_id)
        avg = await self._repo.average_session_minutes(user_id)

        # Step 2 — compute habit strength (deterministic formula)
        top_habits = [
            {
                "goal_title": h["title"],
                "sessions": h["sessions"],
                "total_minutes": h["total_minutes"],
                "habit_strength": round(
                    min(
                        1.0,
                        (h["total_minutes"] / 300) * 0.6
                        + (h["sessions"] / 10) * 0.4,
                    ),
                    2,
                ),
            }
            for h in habits
        ]

        # Step 3 — format time patterns
        time_patterns = [
            {"hour": p["hour"], "sessions": p["sessions"]}
            for p in patterns
        ]

        logger.info(
            "habit_summary_generated",
            user_id=str(user_id),
            habits=len(top_habits),
            patterns=len(time_patterns),
            avg_session_minutes=avg,
        )

        return {
            "top_habits": top_habits,
            "time_patterns": time_patterns,
            "avg_session_minutes": avg,
        }
