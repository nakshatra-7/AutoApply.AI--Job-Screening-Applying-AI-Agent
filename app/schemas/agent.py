from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AgentRunRequest(BaseModel):
    user_id: str
    job_description: str
    goal: Optional[str] = None
    job_context: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None


class AgentStep(BaseModel):
    name: str
    status: str
    tool: Optional[str] = None
    details: Dict[str, Any]


class MissingFieldQuestion(BaseModel):
    field: str
    question: str
    input_type: str = "text"
    options: Optional[List[str]] = None
    required: bool = True


class AgentRunResponse(BaseModel):
    user_id: str
    job_description: str
    steps: List[AgentStep]
    proposed_answers: Dict[str, str]
    missing_fields: List[str] = []
    next_questions: List[MissingFieldQuestion] = []
