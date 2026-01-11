import uuid
from typing import List

from fastapi import HTTPException, status

from app.models.store import ApplicationLogEntry, store


class ApplicationLogService:
    def record(
        self, user_id: str, job_title: str, company: str | None, resume_id: str | None, answers_used: dict[str, str]
    ) -> ApplicationLogEntry:
        if user_id not in store.users:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        entry = ApplicationLogEntry(
            id=str(uuid.uuid4()),
            user_id=user_id,
            job_title=job_title,
            company=company,
            resume_id=resume_id,
            answers_used=answers_used,
        )
        return store.add_application_log(entry)

    def list(self, user_id: str | None = None) -> List[ApplicationLogEntry]:
        if user_id and user_id not in store.users:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user_id:
            return [entry for entry in store.application_logs if entry.user_id == user_id]
        return store.application_logs


application_log_service = ApplicationLogService()

