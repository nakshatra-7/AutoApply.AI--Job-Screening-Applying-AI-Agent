from typing import List, Optional

from pydantic import BaseModel, Field


class ProfileResponse(BaseModel):
    user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    location: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    location: Optional[str] = None


class ResumeUploadResponse(BaseModel):
    resume_id: str
    filename: str
    size_bytes: int
