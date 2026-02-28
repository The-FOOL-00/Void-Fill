"""Transcription service — real speech-to-text via Faster-Whisper.

Provides a true singleton Whisper model that loads once and is reused
across all transcription requests.  Transcription is CPU-heavy and is
always dispatched to a thread executor so the async event loop is never
blocked.
"""

import asyncio
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


class TranscriptionService:
    """Singleton Faster-Whisper transcription engine.

    The underlying ``WhisperModel`` is loaded lazily on first use and
    shared across every subsequent call.  All public methods are async
    and delegate the blocking C++ inference to a thread-pool executor.
    """

    _model = None

    @classmethod
    def get_model(cls):  # type: ignore[no-untyped-def]
        """Return the shared WhisperModel, loading it on first call.

        Uses ``base.en`` with int8 quantisation on CPU for a good
        balance between accuracy and container resource usage.
        """
        if cls._model is None:
            from faster_whisper import WhisperModel

            logger.info("whisper_model_loading", model="base.en", device="cpu", compute_type="int8")
            cls._model = WhisperModel(
                "base.en",
                device="cpu",
                compute_type="int8",
            )
            logger.info("model_loaded", model="base.en")
        return cls._model

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def transcribe_file(self, file_path: str) -> str:
        """Transcribe an audio file and return the full text.

        The blocking Whisper inference is executed inside a thread-pool
        executor so the worker event loop stays responsive.

        Args:
            file_path: Absolute path to the audio file on disk.

        Returns:
            The transcribed text as a single string.

        Raises:
            FileNotFoundError: If *file_path* does not exist.
            RuntimeError: If Whisper fails to produce any segments.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        logger.info("transcription_started", path=file_path)

        loop = asyncio.get_running_loop()
        transcript = await loop.run_in_executor(
            None,
            lambda: self._sync_transcribe(str(path)),
        )

        logger.info("transcription_complete", path=file_path, length=len(transcript))
        return transcript

    # ------------------------------------------------------------------
    # Internal sync helper (runs in executor thread)
    # ------------------------------------------------------------------

    def _sync_transcribe(self, file_path: str) -> str:
        """Run Whisper inference synchronously.

        This method is called inside a thread executor — it must never
        be awaited directly.

        Args:
            file_path: Absolute path to the audio file.

        Returns:
            Concatenated text from all Whisper segments.
        """
        model = self.get_model()
        segments, _info = model.transcribe(
            file_path,
            beam_size=5,
            language="en",
            vad_filter=True,
        )
        text_parts: list[str] = [segment.text.strip() for segment in segments]
        transcript = " ".join(text_parts).strip()

        if not transcript:
            raise RuntimeError(f"Whisper produced empty transcript for {file_path}")

        return transcript
