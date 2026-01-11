from fastapi import APIRouter, HTTPException, status

from app.schemas.job import JobAnalysisRequest, JobAnalysisResponse
from app.services.job import job_analysis_service

router = APIRouter(prefix="/job", tags=["job"])


@router.post("/analyse", response_model=JobAnalysisResponse)
def analyse(payload: JobAnalysisRequest):
    result = job_analysis_service.analyse(
        user_id=payload.user_id,
        job_title=payload.job_title,
        description=payload.description,
        required_skills=payload.required_skills,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return JobAnalysisResponse(**result)

