"""Transcription service — speech-to-text via Gemini API.

Uses Google Gemini 1.5 Flash to transcribe audio files sent as inline
base64 data.  No local model is loaded — all inference runs in the cloud,
making this suitable for memory-constrained deployments (e.g. Railway).
"""

import base64
from pathlib import Path

import google.generativeai as genai

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Map file extensions to MIME types accepted by Gemini
_MIME_MAP: dict[str, str] = {
    ".wav": "audio/wav",
    ".mp3": "audio/mp3",
    ".m4a": "audio/mp4",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}

_TRANSCRIBE_PROMPT = (
    "Transcribe this audio exactly as spoken. "
    "Return only the spoken words with no timestamps, labels, or extra commentary."
)


class TranscriptionService:
    """Cloud-based transcription via Gemini 1.5 Flash.

    No local model is loaded.  Each call encodes the audio file as
    base64 and sends it to the Gemini API, which returns the transcript.
    """

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def transcribe_file(self, file_path: str) -> str:
        """Transcribe an audio file using Gemini and return the full text.

        Args:
            file_path: Absolute path to the audio file on disk.

        Returns:
            The transcribed text as a single string.

        Raises:
            FileNotFoundError: If *file_path* does not exist.
            RuntimeError: If Gemini returns an empty transcript.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        logger.info("transcription_started", path=file_path, engine="gemini")

        mime_type = _MIME_MAP.get(path.suffix.lower(), "audio/wav")

        audio_bytes = path.read_bytes()
        audio_b64 = base64.b64encode(audio_bytes).decode()

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_transcription_model)

        response = await model.generate_content_async([
            {"inline_data": {"mime_type": mime_type, "data": audio_b64}},
            _TRANSCRIBE_PROMPT,
        ])

        transcript = response.text.strip() if response.text else ""

        if not transcript:
            raise RuntimeError(f"Gemini returned empty transcript for {file_path}")

        logger.info("transcription_complete", path=file_path, length=len(transcript))
        return transcript
