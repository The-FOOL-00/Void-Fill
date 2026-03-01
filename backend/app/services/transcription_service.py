"""Transcription service — demo-mode stub (no Whisper).

Whisper / faster-whisper model loading is too slow inside Docker on
CPU, so for the prototype demo we skip real speech-to-text entirely
and return a fixed, realistic transcript.

The rest of the pipeline (LLM intelligence, goal matching, actions,
notes) continues to operate normally on this transcript.
"""

from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Fixed demo transcript — deterministic so the demo is reproducible.
# Contains three distinct, actionable tasks the intelligence pipeline
# can extract: a coding task, hydration reminder, and exercise goal.
# ---------------------------------------------------------------------------
_DEMO_TRANSCRIPT: str = (
    "I need to spend about an hour on my coding project today, "
    "probably work on the backend API. "
    "I also keep forgetting to drink enough water so I should set a reminder for that. "
    "And I want to do a quick 30-minute workout in the evening, maybe some stretching and a jog."
)


class TranscriptionService:
    """Stub transcription service that returns a fixed demo transcript.

    No model is loaded; no audio is actually processed.  The file path
    is validated for existence so the upload pipeline still catches
    missing files early.
    """

    async def transcribe_file(self, file_path: str) -> str:
        """Return the fixed demo transcript.

        Args:
            file_path: Absolute path to the uploaded audio file.

        Returns:
            The demo transcript string.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        logger.info(
            "transcription_demo",
            path=file_path,
            note="Whisper skipped — using fixed demo transcript",
        )
        return _DEMO_TRANSCRIPT
