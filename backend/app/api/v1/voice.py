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
    """Accept an audio file and start transcription processing.

    Returns a job identifier that can be polled via the result endpoint.
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
    """Retrieve the transcription and intent for a previously uploaded voice file."""
    service = VoiceService(db)
    return await service.get_result(user_id, job_id)
