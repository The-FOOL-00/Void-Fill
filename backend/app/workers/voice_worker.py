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

from app.services.transcription_service import TranscriptionService

settings = get_settings()
logger = get_logger(__name__)

_transcription_service = TranscriptionService()


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

            # --- Step 1: Transcription (Faster-Whisper) ---
            transcript = await _transcription_service.transcribe_file(str(audio_path))

            # --- Step 2: Store transcript ---
            await repo.update_transcript(job_id, transcript)
            await session.commit()
            logger.info("transcription_complete", path=str(audio_path))

            # --- Step 3: Intelligence pipeline ---
            intelligence_ok = False
            try:
                from app.services.voice_intelligence_service import VoiceIntelligenceService

                intelligence_service = VoiceIntelligenceService(session)
                await intelligence_service.process_transcript(
                    voice_job_id=job_id,
                    user_id=job.user_id,
                    transcript=transcript,
                )
                await session.commit()
                intelligence_ok = True
            except Exception as e:
                await session.rollback()
                logger.error(
                    "intelligence_processing_failed",
                    job_id=job_id_str,
                    error=str(e),
                )

            # --- Step 4: Autonomous action execution ---
            if intelligence_ok:
                try:
                    from app.services.action_service import ActionService

                    action_service = ActionService(session)
                    await action_service.execute_from_intelligence(
                        job_id=job_id,
                        user_id=job.user_id,
                    )
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    logger.error(
                        "action_execution_failed",
                        job_id=job_id_str,
                        error=str(e),
                    )
            else:
                logger.warning(
                    "action_skipped_no_intelligence",
                    job_id=job_id_str,
                )

            # --- Step 5: Mark completed ---
            final_status = "completed" if intelligence_ok else "partial"
            await repo.update_status(job_id, final_status)
            await session.commit()
            logger.info("job_completed", job_id=job_id_str, status=final_status)

        except Exception as exc:
            await session.rollback()
            async with async_session_factory() as err_session:
                err_repo = VoiceJobRepository(err_session)
                await err_repo.update_error(job_id, str(exc))
                await err_session.commit()
            logger.error("job_failed", job_id=job_id_str, error=str(exc))


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
