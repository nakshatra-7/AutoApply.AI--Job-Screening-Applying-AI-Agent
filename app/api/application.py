from typing import Optional

from fastapi import APIRouter

from app.schemas.application_log import ApplicationLogEntryResponse, ApplicationLogListResponse, ApplicationLogRequest
from app.services.application_log import application_log_service

router = APIRouter(prefix="/application", tags=["application"])


@router.post("/log", response_model=ApplicationLogEntryResponse)
def log_application(payload: ApplicationLogRequest):
    entry = application_log_service.record(
        user_id=payload.user_id,
        job_title=payload.job_title,
        company=payload.company,
        resume_id=payload.resume_id,
        answers_used=payload.answers_used,
    )
    return ApplicationLogEntryResponse(**entry.__dict__)


@router.get("/log", response_model=ApplicationLogListResponse)
def list_logs(user_id: Optional[str] = None):
    entries = application_log_service.list(user_id=user_id)
    return ApplicationLogListResponse(entries=[ApplicationLogEntryResponse(**entry.__dict__) for entry in entries])

