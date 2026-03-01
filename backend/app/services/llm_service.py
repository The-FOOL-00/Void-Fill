"""LLM Intelligence Service — structured transcript analysis via Gemini.

Provides a singleton Gemini generative model that analyses voice transcripts
and returns structured intent data as JSON.  The model is configured once
and reused across all requests.
"""

import asyncio
import json
from typing import Any

import google.generativeai as genai

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are the VoidFill AI brain.

Analyze a voice transcript and return structured JSON.

Valid intents:

goal_create — User expresses something they want or need to do.
  Examples: "I need to study math", "I should exercise", "I want to learn Python"

schedule_create — User specifies a time for an activity.
  Examples: "Study math at 7pm", "Gym tomorrow morning"

note_create — User records information or a reflection.
  Examples: "I learned derivatives today", "I understood integrals"

void_query — User asks what to do next.
  Examples: "What should I do now?", "What's next?"

unknown — Anything that does not match the above.

Return strict JSON only. No markdown fences. No explanation.

Format:

{
  "intent": "goal_create | schedule_create | note_create | void_query | unknown",
  "confidence": 0.0-1.0,
  "goal_title": "string or null",
  "schedule_time": "string or null (e.g. '7pm', 'tomorrow morning', '3:30pm')",
  "schedule_activity": "string or null (e.g. 'Study math', 'Gym session', 'Doctor appointment')",
  "note_text": "string or null"
}
"""

_VALID_INTENTS: frozenset[str] = frozenset({
    "goal_create",
    "schedule_create",
    "note_create",
    "void_query",
    "unknown",
})

_FALLBACK_RESULT: dict[str, Any] = {
    "intent": "unknown",
    "confidence": 0.0,
    "goal_title": None,
    "schedule_time": None,
    "schedule_activity": None,
    "note_text": None,
}


class LLMService:
    """Gemini generative model for transcript intelligence.

    The ``GenerativeModel`` is configured on instantiation.  The blocking
    ``generate_content`` call is dispatched to a thread executor so the
    async event loop is never blocked.
    """

    def __init__(self) -> None:
        settings = get_settings()

        api_key = settings.gemini_api_key
        model_name = settings.gemini_model

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        if not model_name:
            raise RuntimeError("GEMINI_MODEL is not set")

        genai.configure(api_key=api_key)

        self._model = genai.GenerativeModel(model_name)

        logger.info(
            "llm_client_initialised",
            provider="gemini",
            model=model_name,
        )

    async def analyze_transcript(self, text: str) -> dict[str, Any]:
        """Send a transcript to Gemini and return structured intent JSON.

        The blocking SDK call is dispatched to a thread executor.  On any
        failure (network, parsing, invalid response) the method returns a
        safe fallback with ``intent="unknown"`` so the worker pipeline
        never crashes.

        Args:
            text: Raw transcript text to analyse.

        Returns:
            A dict with keys: intent, confidence, goal_title,
            schedule_time, note_text.
        """
        logger.info("llm_request_started", text_length=len(text))

        try:
            prompt = f"{_SYSTEM_PROMPT}\n\nTranscript:\n{text}"

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._model.generate_content(prompt),
            )

            raw = response.text.strip()
            logger.info("llm_response_received", raw_length=len(raw))

            result = self._parse_response(raw)
            return result

        except Exception as exc:
            logger.error("llm_failed", error=str(exc))
            return dict(_FALLBACK_RESULT)

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(raw: str) -> dict[str, Any]:
        """Extract and validate JSON from the LLM response string.

        Handles markdown fenced code blocks, trailing text, and
        malformed JSON gracefully.

        Args:
            raw: The raw string content from the LLM response.

        Returns:
            A validated dict with all required keys.
        """
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("llm_json_parse_failed", raw=raw[:200])
            return dict(_FALLBACK_RESULT)

        # Validate intent
        intent = data.get("intent", "unknown")
        if intent not in _VALID_INTENTS:
            intent = "unknown"

        # Validate confidence
        try:
            confidence = float(data.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = 0.0

        return {
            "intent": intent,
            "confidence": round(confidence, 2),
            "goal_title": data.get("goal_title"),
            "schedule_time": data.get("schedule_time"),
            "schedule_activity": data.get("schedule_activity"),
            "note_text": data.get("note_text"),
        }


# ------------------------------------------------------------------
# Factory function — replaces fragile singleton pattern
# ------------------------------------------------------------------
_llm_service_instance: LLMService | None = None


def get_llm_service() -> LLMService:
    """Return a module-level LLMService instance, created on first call.

    This replaces the old ``__new__``-based singleton which was prone to
    corruption when the class body wasn't fully loaded at import time.
    """
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance
