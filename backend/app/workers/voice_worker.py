"""Background voice processing worker.

Runs as a standalone process that polls the Redis queue for voice jobs,
transcribes audio files, runs the intelligence pipeline, and stores
the results in PostgreSQL.

Usage:
    python -m app.workers.voice_worker
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Ensure the backend directory is on sys.path when run directly
_backend_dir = str(Path(__file__).resolve().parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.core.config import get_settings
from app.core.database import async_session_factory, init_db
from app.core.logging import get_logger, setup_logging
from app.core.redis import close_redis, dequeue_voice_job
from app.repositories.voice_job_repository import VoiceJobRepository
from app.services.voice_intelligence_service import VoiceIntelligenceService

settings = get_settings()
logger = get_logger(__name__)

MOCK_TRANSCRIPT: str = (
    "This is a sample transcript from VoidFill voice processing."
)


async def process_job(job_id_str: str) -> None:
    """Process a single voice job end-to-end.

    Lifecycle: queued → processing → transcribe → intelligence → completed | failed

    Args:
        job_id_str: The string UUID of the voice job to process.
    """
    job_id = UUID(job_id_str)
    logger.info("processing_job", job_id=job_id_str)

    async with async_session_factory() as session:
        repo = VoiceJobRepository(session)

        # Mark as processing
        job = await repo.update_status(job_id, "processing")
        if job is None:
            logger.error("job_not_found", job_id=job_id_str)
            await session.commit()
            return

        try:
            # Verify the audio file exists
            audio_path = Path(job.audio_path)
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # --- Step 1: Transcription (mock Whisper) ---
            transcript = await transcribe_audio(audio_path)

            # --- Step 2: Store transcript ---
            await repo.update_transcript(job_id, transcript)
            await session.commit()
            logger.info("transcript_stored", job_id=job_id_str)

        except Exception as exc:
            await session.rollback()
            async with async_session_factory() as err_session:
                err_repo = VoiceJobRepository(err_session)
                await err_repo.update_error(job_id, str(exc))
                await err_session.commit()
            logger.error("job_failed", job_id=job_id_str, error=str(exc))
            return

    # --- Step 3: Intelligence pipeline (separate transaction) ---
    try:
        async with async_session_factory() as intel_session:
            intel_service = VoiceIntelligenceService(intel_session)
            record = await intel_service.process_transcript(
                voice_job_id=job_id,
                user_id=job.user_id,
                transcript=transcript,
            )
            await intel_session.commit()
            logger.info(
                "intelligence_complete",
                job_id=job_id_str,
                intent=record.intent,
            )
    except Exception as exc:
        logger.error(
            "intelligence_failed",
            job_id=job_id_str,
            error=str(exc),
        )

    logger.info("job_completed", job_id=job_id_str)


async def transcribe_audio(audio_path: Path) -> str:
    """Transcribe an audio file to text.

    Currently returns a deterministic mock transcript.
    Will be replaced by Whisper / faster-whisper integration.

    Args:
        audio_path: Path to the audio file on disk.

    Returns:
        The transcribed text.
    """
    # Simulate processing latency
    await asyncio.sleep(1)
    logger.info("transcription_complete", path=str(audio_path))
    return MOCK_TRANSCRIPT


async def worker_loop() -> None:
    """Run the infinite polling loop that drains the voice job queue.

    Catches all exceptions inside the loop body so the worker never
    crashes.  Logs every state transition for observability.
    """
    logger.info("voice_worker_started")

    while True:
        try:
            job_id_str = await dequeue_voice_job()

            if job_id_str is None:
                # Queue empty — brpop already waited 2 s, loop again
                continue

            logger.info("job_received", job_id=job_id_str)
            await process_job(job_id_str)

        except Exception as exc:
            # Guard: never let the loop die
            logger.error("worker_loop_error", error=str(exc))
            await asyncio.sleep(2)


async def main() -> None:
    """Entry-point: initialise dependencies and start the worker loop."""
    setup_logging()
    logger.info("worker_initialising")

    # Ensure tables exist (idempotent)
    await init_db()

    try:
        await worker_loop()
    finally:
        await close_redis()
        logger.info("voice_worker_shutdown")


if __name__ == "__main__":
    asyncio.run(main())
