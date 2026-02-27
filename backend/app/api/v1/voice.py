"""Voice endpoints — upload audio and retrieve transcription results."""

from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.voice_schema import VoiceResultResponse, VoiceUploadResponse
from app.services.voice_service import VoiceService

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post(
    "/upload",
    response_model=VoiceUploadResponse,
    status_code=201,
    summary="Upload a voice file for transcription",
)
async def upload_voice(
    file: UploadFile = File(..., description="Audio file (wav, mp3, m4a, webm)"),
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VoiceUploadResponse:
    """Accept an audio file, create a processing job, and return immediately.

    The job is enqueued onto a Redis queue for background transcription.
    Poll ``GET /voice/result/{job_id}`` to retrieve the transcript.
    """
    service = VoiceService(db)
    return await service.upload(user_id, file)


@router.get(
    "/result/{job_id}",
    response_model=VoiceResultResponse,
    summary="Get voice transcription result",
)
async def get_voice_result(
    job_id: UUID,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VoiceResultResponse:
    """Retrieve the current status and transcript for a voice processing job.

    ``transcript`` is ``null`` until the job reaches ``completed`` status.
    """
    service = VoiceService(db)
    return await service.get_result(user_id, job_id)
