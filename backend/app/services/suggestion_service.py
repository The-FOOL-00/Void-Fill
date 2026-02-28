"""Service layer for AI suggestion generation."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.suggestion import Suggestion
from app.repositories.goal_repository import GoalRepository
from app.repositories.suggestion_repository import SuggestionRepository
from app.services.memory_service import MemoryService
from app.schemas.suggestion_schema import (
    SuggestionListResponse,
    SuggestionRequest,
    SuggestionResponse,
)

logger = get_logger(__name__)


class SuggestionService:
    """Generates and retrieves AI-powered suggestions for a user."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SuggestionRepository(session)
        self._goal_repo = GoalRepository(session)

    async def request_suggestions(
        self, user_id: UUID, payload: SuggestionRequest
    ) -> SuggestionListResponse:
        """Generate new suggestions for the user.

        When a ``goal_id`` is provided the suggestions are scoped to that
        goal.  Otherwise they are general productivity recommendations.

        The LLM parsing service will replace the placeholder generation
        logic below.

        Args:
            user_id: The authenticated user's UUID.
            payload: Request parameters including optional goal_id and limit.

        Returns:
            A list of newly created suggestions.
        """
        goal_title: Optional[str] = None
        if payload.goal_id is not None:
            goal = await self._goal_repo.get_by_id(payload.goal_id)
            if goal is not None and goal.user_id == user_id:
                goal_title = goal.title

        generated = self._generate(
            user_id=user_id,
            goal_id=payload.goal_id,
            goal_title=goal_title,
            limit=payload.limit,
        )

        persisted = await self._repo.create_many(generated)

        items = [SuggestionResponse.model_validate(s) for s in persisted]
        logger.info(
            "suggestions_generated",
            user_id=str(user_id),
            count=len(items),
            goal_id=str(payload.goal_id) if payload.goal_id else None,
        )
        return SuggestionListResponse(suggestions=items, count=len(items))

    async def list_suggestions(
        self, user_id: UUID, goal_id: Optional[UUID] = None, limit: int = 20
    ) -> SuggestionListResponse:
        """Retrieve existing suggestions for the user.

        Args:
            user_id: The authenticated user's UUID.
            goal_id: Optional goal filter.
            limit: Maximum results.

        Returns:
            A list wrapper with count.
        """
        suggestions = await self._repo.list_by_user(user_id, goal_id=goal_id, limit=limit)
        items = [SuggestionResponse.model_validate(s) for s in suggestions]
        return SuggestionListResponse(suggestions=items, count=len(items))

    async def get_ranked_suggestions(
        self,
        user_id: UUID,
        void_minutes: int,
        limit: int = 5,
    ) -> list[Suggestion]:
        """Return suggestions ranked by goal-aware scoring.

        Steps:
        1. Load a broad pool of suggestions from the database.
        2. Filter to those whose ``estimated_minutes`` fits the void.
        3. Score each suggestion with a weighted formula.
        4. Sort descending by final score and return top *limit*.

        If no suggestions fit the void duration, the shortest ones are
        returned so the list is never empty.

        Args:
            user_id: The authenticated user's UUID.
            void_minutes: Available free time in minutes.
            limit: Maximum suggestions to return (default 5).

        Returns:
            List of ``(final_score, Suggestion)`` tuples, sorted descending.
        """
        # Guard: zero or negative void → nothing useful to suggest
        if void_minutes <= 0:
            logger.info(
                "suggestions_ranked",
                user_id=str(user_id),
                void_minutes=void_minutes,
                count=0,
            )
            return []

        # Step 1 — load broad pool
        pool = await self._repo.list_by_user(user_id=user_id, limit=50)

        if not pool:
            logger.info(
                "suggestions_ranked",
                user_id=str(user_id),
                void_minutes=void_minutes,
                count=0,
            )
            return []

        # Step 2 — filter by duration
        fitting = [
            s for s in pool
            if s.estimated_minutes is not None and s.estimated_minutes <= void_minutes
        ]

        # Fallback: if nothing fits, return the shortest suggestions
        if not fitting:
            pool_with_est = [s for s in pool if s.estimated_minutes is not None]
            if pool_with_est:
                pool_with_est.sort(key=lambda s: s.estimated_minutes)  # type: ignore[arg-type]
                fitting = pool_with_est[:limit]
            else:
                # No estimated_minutes at all — fall back to raw score order
                fitting = pool[:limit]

        # Step 3 — load memory summary for adaptive boosting
        memory_service = MemoryService(self._session)
        summary = await memory_service.get_summary(user_id)

        # Step 4 — build goal memory map {goal_id: total_minutes, title: total_minutes}
        goal_minutes_by_id: dict[str, int] = {}
        goal_minutes_by_title: dict[str, int] = {}
        for g in summary.get("top_goals") or []:
            if g.get("goal_id") is not None:
                goal_minutes_by_id[str(g["goal_id"])] = g["total_minutes"]
            if g.get("title"):
                goal_minutes_by_title[g["title"].lower()] = g["total_minutes"]

        all_minutes = list(goal_minutes_by_id.values()) + list(goal_minutes_by_title.values())
        max_minutes = max(all_minutes, default=0)

        # Step 5 — score each suggestion with memory boost
        scored: list[tuple[float, Suggestion]] = []
        for s in fitting:
            est = s.estimated_minutes if s.estimated_minutes is not None else 0
            if void_minutes > 0 and est > 0:
                duration_fit = max(
                    0.0,
                    min(1.0, 1 - abs(void_minutes - est) / void_minutes),
                )
            else:
                duration_fit = 0.0

            # Memory boost: match by goal_id first, then by title substring
            mem_minutes = 0
            if s.goal_id is not None and str(s.goal_id) in goal_minutes_by_id:
                mem_minutes = goal_minutes_by_id[str(s.goal_id)]
            else:
                s_text_lower = s.text.lower() if s.text else ""
                for title, minutes in goal_minutes_by_title.items():
                    if title in s_text_lower or s_text_lower in title:
                        mem_minutes = max(mem_minutes, minutes)

            memory_boost = mem_minutes / max_minutes if max_minutes > 0 else 0.0

            final_score = s.score * 0.5 + duration_fit * 0.3 + memory_boost * 0.2
            final_score = max(0.0, min(1.0, final_score))
            scored.append((final_score, s))

        # Step 6 — sort descending
        scored.sort(key=lambda t: t[0], reverse=True)

        # Step 7 — return top N as (final_score, Suggestion) tuples
        ranked = scored[:limit]

        logger.info(
            "suggestions_ranked",
            user_id=str(user_id),
            void_minutes=void_minutes,
            count=len(ranked),
        )
        logger.info(
            "suggestions_adapted",
            void_minutes=void_minutes,
            suggestions=len(ranked),
            memory_goals=len(goal_minutes_by_id) + len(goal_minutes_by_title),
        )
        return ranked

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate(
        user_id: UUID,
        goal_id: Optional[UUID],
        goal_title: Optional[str],
        limit: int,
    ) -> list[Suggestion]:
        """Create placeholder suggestion ORM instances.

        The LLM module will replace this with real generation logic.

        Args:
            user_id: User UUID.
            goal_id: Optional goal UUID.
            goal_title: Optional goal title for context.
            limit: Number of suggestions to produce.

        Returns:
            List of unsaved Suggestion ORM instances.
        """
        suggestions: list[Suggestion] = []
        context = f" for goal '{goal_title}'" if goal_title else ""

        durations = [15, 30, 45, 60, 90]
        for idx in range(limit):
            score = round(1.0 - (idx * 0.1), 2)
            est = durations[idx % len(durations)]
            suggestions.append(
                Suggestion(
                    user_id=user_id,
                    goal_id=goal_id,
                    text=f"Suggestion {idx + 1}{context}: optimise your next void slot",
                    score=max(score, 0.1),
                    estimated_minutes=est,
                    accepted=False,
                )
            )
        return suggestions
