from fastapi import APIRouter

from app.schemas.github import GitHubConnectRequest, GitHubConnectResponse, GitHubSyncResponse
from app.services.github import github_service

router = APIRouter(prefix="/github", tags=["github"])


@router.post("/connect", response_model=GitHubConnectResponse)
def connect(payload: GitHubConnectRequest):
    connection = github_service.connect(payload.user_id, payload.access_token)
    return GitHubConnectResponse(user_id=connection.user_id, connected_at=connection.connected_at)


@router.post("/sync", response_model=GitHubSyncResponse)
def sync(payload: GitHubConnectRequest):
    repos = github_service.sync(payload.user_id)
    return GitHubSyncResponse(user_id=payload.user_id, repos=repos)

