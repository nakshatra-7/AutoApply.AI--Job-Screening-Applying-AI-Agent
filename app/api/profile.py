from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest, ResumeUploadResponse
from app.services.profile import profile_service

router = APIRouter(prefix="/profile", tags=["profile"])
resume_router = APIRouter(prefix="/resume", tags=["resume"])


@router.get("/get", response_model=ProfileResponse)
def get_profile(user_id: str, db: Session = Depends(get_db)):
    profile = profile_service.get_profile(user_id, db=db)
    return ProfileResponse(**profile.__dict__)


@router.put("/update", response_model=ProfileResponse)
def update_profile(payload: ProfileUpdateRequest, db: Session = Depends(get_db)):
    profile = profile_service.update_profile(
        user_id=payload.user_id,
        db=db,
        first_name=payload.first_name,
        last_name=payload.last_name,
        address_line1=payload.address_line1,
        city=payload.city,
        postal_code=payload.postal_code,
        phone=payload.phone,
        country=payload.country,
        headline=payload.headline,
        summary=payload.summary,
        skills=payload.skills,
        location=payload.location,
    )
    return ProfileResponse(**profile.__dict__)


@resume_router.post("/upload", response_model=ResumeUploadResponse)
def upload_resume(user_id: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    resume = profile_service.upload_resume(user_id=user_id, file=file, db=db)
    return ResumeUploadResponse(resume_id=resume.id, filename=resume.filename, size_bytes=resume.size_bytes)
