from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class ApplicationLogRequest(BaseModel):
    user_id: str
    job_title: str
    company: Optional[str] = None
    resume_id: Optional[str] = None
    answers_used: Dict[str, str]


class ApplicationLogEntryResponse(BaseModel):
    id: str
    user_id: str
    job_title: str
    company: Optional[str] = None
    resume_id: Optional[str] = None
    answers_used: Dict[str, str]
    applied_at: datetime


class ApplicationLogListResponse(BaseModel):
    entries: List[ApplicationLogEntryResponse]
