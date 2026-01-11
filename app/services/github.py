from typing import List

from fastapi import HTTPException, status

from app.models.store import GitHubConnection, store
from app.schemas.github import GitHubRepo


class GitHubService:
    def connect(self, user_id: str, access_token: str) -> GitHubConnection:
        if user_id not in store.users:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        connection = GitHubConnection(user_id=user_id, access_token=access_token)
        return store.add_github_connection(connection)

    def sync(self, user_id: str) -> List[GitHubRepo]:
        if user_id not in store.users:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user_id not in store.github_connections:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub not connected")

        # Placeholder sync that returns mock repo data.
        return [
            GitHubRepo(name="auto-job-filler", description="Autofills job applications", stars=42, language="Python"),
            GitHubRepo(name="resume-parser", description="Parses resumes for key skills", stars=18, language="TypeScript"),
        ]


github_service = GitHubService()

