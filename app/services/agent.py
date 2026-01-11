from typing import Any, Dict, Optional, Tuple, List

from app.models.store import Profile
from app.schemas.agent import AgentStep
from app.services.agent_orchestrator import agent_orchestrator


def run(
    user_id: str,
    job_description: str,
    goal: Optional[str] = None,
    job_context: Optional[Dict[str, Any]] = None,
    user_profile: Optional[Profile] = None,
    constraints: Optional[Dict[str, Any]] = None,
    db: Any = None,
    return_meta: bool = False,
) -> Tuple[List[AgentStep], Dict[str, str]] | Tuple[List[AgentStep], Dict[str, str], Dict[str, Any]]:
    """
    Backward-compatible wrapper.

    Orchestrator signature:
      run(user_id, goal, job_context, user_profile, constraints=None, db=None)
    """
    constraints = constraints or {}

    # Build context (always ensure job_description is present)
    context: Dict[str, Any] = dict(job_context or {})
    context.setdefault("job_description", job_description)

    # Default goal if not provided
    goal = goal or "Generate application package for this job"

    result = agent_orchestrator.run(
        user_id=user_id,
        goal=goal,
        job_context=context,
        user_profile=user_profile,
        constraints=constraints,
        db=db,
        return_meta=return_meta,
    )
    return result
