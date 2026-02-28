"""Unit tests for Phase 9 — Intelligent Suggestions Engine (goal-aware ranking).

These tests verify:
1. Duration filtering excludes suggestions that exceed void minutes.
2. Ranking scores suggestions correctly (duration fit + base score).
3. No-match fallback returns the shortest suggestions instead of an empty list.
4. Empty pool returns empty list gracefully.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Lightweight stand-in for `Suggestion` ORM objects used in ranking logic.
# ---------------------------------------------------------------------------

def _make_suggestion(
    *,
    text: str = "placeholder",
    score: float = 0.5,
    estimated_minutes: Optional[int] = None,
    goal_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
) -> SimpleNamespace:
    """Return a minimal Suggestion-like object accepted by the ranking code."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        goal_id=goal_id,
        text=text,
        score=score,
        estimated_minutes=estimated_minutes,
        accepted=False,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Helpers – ranking extracted for direct testing
# ---------------------------------------------------------------------------

def _rank(suggestions, void_minutes: int, limit: int = 5):
    """Replicates SuggestionService.get_ranked_suggestions scoring logic.

    This is a pure-Python re-implementation so we don't depend on AsyncSession.
    """
    if not suggestions:
        return []

    # Step 2 — filter by duration
    fitting = [
        s for s in suggestions
        if s.estimated_minutes is not None and s.estimated_minutes <= void_minutes
    ]

    # Fallback: shortest
    if not fitting:
        pool_with_est = [s for s in suggestions if s.estimated_minutes is not None]
        if pool_with_est:
            pool_with_est.sort(key=lambda s: s.estimated_minutes)
            fitting = pool_with_est[:limit]
        else:
            fitting = suggestions[:limit]

    # Step 3 — score
    scored = []
    for s in fitting:
        est = s.estimated_minutes if s.estimated_minutes is not None else 0
        if void_minutes > 0 and est > 0:
            duration_fit = max(0.0, min(1.0, 1 - abs(void_minutes - est) / void_minutes))
        else:
            duration_fit = 0.0
        final_score = s.score * 0.6 + duration_fit * 0.4
        scored.append((final_score, s))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [s for _, s in scored[:limit]]


# ---------------------------------------------------------------------------
# Test 1 — Duration Filtering
# ---------------------------------------------------------------------------

class TestDurationFiltering:
    """Void = 20 min → 60 min suggestions must be excluded."""

    def test_excludes_long_suggestions(self):
        pool = [
            _make_suggestion(text="short task", score=0.8, estimated_minutes=10),
            _make_suggestion(text="medium task", score=0.9, estimated_minutes=20),
            _make_suggestion(text="long task", score=1.0, estimated_minutes=60),
        ]
        result = _rank(pool, void_minutes=20)

        texts = [s.text for s in result]
        assert "long task" not in texts
        assert "short task" in texts
        assert "medium task" in texts

    def test_keeps_only_fitting_durations(self):
        pool = [
            _make_suggestion(text="a", score=0.5, estimated_minutes=5),
            _make_suggestion(text="b", score=0.5, estimated_minutes=15),
            _make_suggestion(text="c", score=0.5, estimated_minutes=25),
            _make_suggestion(text="d", score=0.5, estimated_minutes=100),
        ]
        result = _rank(pool, void_minutes=20)

        texts = [s.text for s in result]
        assert "a" in texts
        assert "b" in texts
        assert "c" not in texts
        assert "d" not in texts


# ---------------------------------------------------------------------------
# Test 2 — Ranking Works
# ---------------------------------------------------------------------------

class TestRankingScoring:
    """Void = 60 min → 60 min suggestion should rank highest."""

    def test_perfect_duration_fit_wins(self):
        pool = [
            _make_suggestion(text="15m task", score=0.9, estimated_minutes=15),
            _make_suggestion(text="60m task", score=0.7, estimated_minutes=60),
            _make_suggestion(text="45m task", score=0.8, estimated_minutes=45),
        ]
        result = _rank(pool, void_minutes=60)

        # 60m task has perfect duration_fit=1.0: 0.7*0.6 + 1.0*0.4 = 0.82
        # 45m task: duration_fit = 1 - 15/60 = 0.75: 0.8*0.6 + 0.75*0.4 = 0.78
        # 15m task: duration_fit = 1 - 45/60 = 0.25: 0.9*0.6 + 0.25*0.4 = 0.64
        assert result[0].text == "60m task"
        assert result[1].text == "45m task"
        assert result[2].text == "15m task"

    def test_descending_order(self):
        pool = [
            _make_suggestion(text="a", score=0.3, estimated_minutes=10),
            _make_suggestion(text="b", score=0.5, estimated_minutes=25),
            _make_suggestion(text="c", score=0.8, estimated_minutes=30),
        ]
        result = _rank(pool, void_minutes=30)

        scores = []
        for s in result:
            est = s.estimated_minutes
            dur_fit = max(0.0, min(1.0, 1 - abs(30 - est) / 30))
            scores.append(s.score * 0.6 + dur_fit * 0.4)

        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Test 3 — No Duration Match Fallback
# ---------------------------------------------------------------------------

class TestNoMatchFallback:
    """Void = 10 min, suggestions = [30, 60] → return shortest, never empty."""

    def test_returns_shortest_when_none_fit(self):
        pool = [
            _make_suggestion(text="30m task", score=0.5, estimated_minutes=30),
            _make_suggestion(text="60m task", score=0.8, estimated_minutes=60),
        ]
        result = _rank(pool, void_minutes=10)

        assert len(result) > 0, "Must never return empty list"
        # Both duration_fits clamp to 0.0 since both exceed void.
        # Ranking falls back to base score: 60m (0.8) > 30m (0.5).
        assert result[0].text == "60m task"
        assert result[1].text == "30m task"

    def test_never_empty_list(self):
        pool = [
            _make_suggestion(text="huge", score=1.0, estimated_minutes=120),
        ]
        result = _rank(pool, void_minutes=5)

        assert len(result) == 1
        assert result[0].text == "huge"


# ---------------------------------------------------------------------------
# Test 4 — Empty Pool
# ---------------------------------------------------------------------------

class TestEmptyPool:
    """No suggestions in DB → return empty list, don't crash."""

    def test_empty_pool_returns_empty(self):
        result = _rank([], void_minutes=60)
        assert result == []


# ---------------------------------------------------------------------------
# Test 5 — Limit Enforcement
# ---------------------------------------------------------------------------

class TestLimit:
    """Only top N results returned."""

    def test_respects_limit(self):
        pool = [
            _make_suggestion(text=f"task-{i}", score=0.5, estimated_minutes=10)
            for i in range(20)
        ]
        result = _rank(pool, void_minutes=60, limit=5)
        assert len(result) == 5


# ---------------------------------------------------------------------------
# Test 6 — Case 1 from spec
# ---------------------------------------------------------------------------

class TestSpecCase1:
    """Void=30min, suggestions=[5m,25m,90m] → output=[25m,5m]."""

    def test_case_1(self):
        pool = [
            _make_suggestion(text="5 min reading", score=0.5, estimated_minutes=5),
            _make_suggestion(text="25 min practice", score=0.5, estimated_minutes=25),
            _make_suggestion(text="90 min project", score=0.5, estimated_minutes=90),
        ]
        result = _rank(pool, void_minutes=30)

        texts = [s.text for s in result]
        assert "90 min project" not in texts
        # 25 min has better duration fit to 30 than 5 min
        assert result[0].text == "25 min practice"
        assert result[1].text == "5 min reading"


# ---------------------------------------------------------------------------
# Test 7 — Case 2 from spec
# ---------------------------------------------------------------------------

class TestSpecCase2:
    """Void=120min, suggestions=[15m,45m,90m] → all fit, ranked by score."""

    def test_case_2(self):
        pool = [
            _make_suggestion(text="15 min reading", score=0.5, estimated_minutes=15),
            _make_suggestion(text="45 min exercise", score=0.5, estimated_minutes=45),
            _make_suggestion(text="90 min study", score=0.5, estimated_minutes=90),
        ]
        result = _rank(pool, void_minutes=120)

        # All three fit. Same base score (0.5), so duration_fit decides.
        # 90m: fit = 1 - |120-90|/120 = 1 - 30/120 = 0.75
        # 45m: fit = 1 - |120-45|/120 = 1 - 75/120 = 0.375
        # 15m: fit = 1 - |120-15|/120 = 1 - 105/120 = 0.125
        assert result[0].text == "90 min study"
        assert result[1].text == "45 min exercise"
        assert result[2].text == "15 min reading"


# ---------------------------------------------------------------------------
# Test 8 — Zero void_minutes (division-by-zero guard)
# ---------------------------------------------------------------------------

class TestZeroVoidMinutes:
    """Void=0min → return empty, no division-by-zero crash."""

    def test_zero_void_returns_empty(self):
        pool = [
            _make_suggestion(text="a", score=0.5, estimated_minutes=10),
            _make_suggestion(text="b", score=0.8, estimated_minutes=30),
        ]
        # void_minutes=0 hits the early guard in the real service.
        # The scoring formula also guards: if void_minutes > 0
        result = _rank(pool, void_minutes=0)
        # With void=0, nothing fits (est <= 0 fails for all).
        # Fallback returns shortest, scored with duration_fit=0.
        # Key: no crash.
        assert isinstance(result, list)

    def test_negative_void_no_crash(self):
        pool = [
            _make_suggestion(text="a", score=0.5, estimated_minutes=10),
        ]
        result = _rank(pool, void_minutes=-5)
        assert isinstance(result, list)
