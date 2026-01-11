from typing import Dict, List, Optional

from pydantic import BaseModel


class JobAnalysisRequest(BaseModel):
    user_id: str
    job_title: str
    description: str
    required_skills: Optional[List[str]] = None


class JobAnalysisResponse(BaseModel):
    job_title: str
    keywords: List[str]
    score_against_profile: float
    suggested_resume_id: Optional[str] = None
    recommendations: Dict[str, str]
