from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class GitHubConnectRequest(BaseModel):
    user_id: str
    access_token: str


class GitHubConnectResponse(BaseModel):
    user_id: str
    connected_at: datetime


class GitHubRepo(BaseModel):
    name: str
    description: Optional[str] = None
    stars: int = 0
    language: Optional[str] = None


class GitHubSyncResponse(BaseModel):
    user_id: str
    repos: List[GitHubRepo]
