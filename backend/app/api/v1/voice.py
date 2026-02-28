"""Voice endpoints — upload, transcription results, and intelligence."""

from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.security import get_current_user
from app.repositories.voice_intelligence_repository import VoiceIntelligenceRepository
from app.repositories.voice_job_repository import VoiceJobRepository
from app.schemas.voice_intelligence_schema import VoiceIntelligenceResponse
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


@router.get(
    "/intelligence/{job_id}",
    response_model=VoiceIntelligenceResponse,
    summary="Get intelligence analysis for a voice job",
)
async def get_voice_intelligence(
    job_id: UUID,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VoiceIntelligenceResponse:
    """Retrieve the parsed intent, extracted text, and matched goal for a voice job.

    Returns 404 if the intelligence record has not been created yet
    (i.e. the worker has not finished processing).
    """
    # Verify the job belongs to this user
    job_repo = VoiceJobRepository(db)
    job = await job_repo.get_job(job_id)
    if job is None or job.user_id != user_id:
        raise NotFoundError("VoiceJob", job_id)

    intel_repo = VoiceIntelligenceRepository(db)
    record = await intel_repo.get_by_job_id(job_id)
    if record is None:
        raise NotFoundError("VoiceIntelligence", job_id)

    return VoiceIntelligenceResponse(
        job_id=record.voice_job_id,
        intent=record.intent,
        confidence=record.confidence,
        extracted_text=record.extracted_text,
        goal_id=record.goal_id,
        created_at=record.created_at,
    )
