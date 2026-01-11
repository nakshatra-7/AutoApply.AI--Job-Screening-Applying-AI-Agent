from fastapi import APIRouter, HTTPException, status

from app.schemas.agent import AgentRunRequest, AgentRunResponse, AgentStep
from app.services.agent_orchestrator import agent_orchestrator
import uuid

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse)
def run(payload: AgentRunRequest):
    user_id = uuid.UUID(payload.user_id)
    goal = payload.goal or f"Autofill application for job: {payload.job_description}"
    job_context = payload.job_context or {"job_description": payload.job_description}
    steps, answers, meta = agent_orchestrator.run(
        user_id=user_id,
        goal=goal,
        job_context=job_context,
        user_profile=None,
        constraints=payload.constraints,
        return_meta=True,
    )
    return AgentRunResponse(
        user_id=str(user_id),
        job_description=payload.job_description,
        steps=steps,
        proposed_answers=answers,
        missing_fields=meta.get("missing_fields", []),
        next_questions=meta.get("next_questions", []),
    )


@router.post("/continue", response_model=AgentRunResponse)
def continue_run(payload: AgentRunRequest):
    if payload.user_inputs is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_inputs is required")
    user_id = uuid.UUID(payload.user_id)
    goal = payload.goal or f"Autofill application for job: {payload.job_description}"
    job_context = payload.job_context or {"job_description": payload.job_description}
    steps, answers, meta = agent_orchestrator.run(
        user_id=payload.user_id,
        goal=goal,
        job_context=job_context,
        user_profile=None,
        constraints=payload.constraints,
        user_inputs=payload.user_inputs,
        return_meta=True,
    )
    return AgentRunResponse(
        user_id=str(user_id),
        job_description=payload.job_description,
        steps=steps,
        proposed_answers=answers,
        missing_fields=meta.get("missing_fields", []),
        next_questions=meta.get("next_questions", []),
    )
