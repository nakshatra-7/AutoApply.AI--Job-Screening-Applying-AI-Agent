from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    full_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Profile:
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
    skills: List[str] = field(default_factory=list)
    location: Optional[str] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResumeRecord:
    id: str
    user_id: str
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime = field(default_factory=datetime.utcnow)
    notes: Optional[str] = None
    parsed_json: Optional[Dict[str, str]] = None


@dataclass
class ApplicationLogEntry:
    id: str
    user_id: str
    job_title: str
    company: Optional[str]
    resume_id: Optional[str]
    answers_used: Dict[str, str] = field(default_factory=dict)
    applied_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GitHubConnection:
    user_id: str
    access_token: str
    connected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


class InMemoryStore:
    """Very small in-memory store to keep the API usable without a DB."""

    def __init__(self) -> None:
        self.users: Dict[str, User] = {}
        self.users_by_email: Dict[str, str] = {}
        self.profiles: Dict[str, Profile] = {}
        self.resumes: Dict[str, ResumeRecord] = {}
        self.tokens: Dict[str, Tuple[str, datetime]] = {}
        self.refresh_tokens: Dict[str, Tuple[str, datetime]] = {}
        self.github_connections: Dict[str, GitHubConnection] = {}
        self.application_logs: List[ApplicationLogEntry] = []

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def create_user(self, email: str, password: str, full_name: Optional[str]) -> User:
        if email in self.users_by_email:
            raise ValueError("User already exists")
        user_id = str(uuid.uuid4())
        user = User(id=user_id, email=email, password_hash=self.hash_password(password), full_name=full_name)
        self.users[user_id] = user
        self.users_by_email[email] = user_id
        return user

    def verify_user(self, email: str, password: str) -> Optional[User]:
        user_id = self.users_by_email.get(email)
        if not user_id:
            return None
        user = self.users[user_id]
        if user.password_hash != self.hash_password(password):
            return None
        return user

    def issue_tokens(self, user_id: str, access_ttl: timedelta, refresh_ttl: timedelta) -> TokenPair:
        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        access_expires = datetime.utcnow() + access_ttl
        refresh_expires = datetime.utcnow() + refresh_ttl
        self.tokens[access_token] = (user_id, access_expires)
        self.refresh_tokens[refresh_token] = (user_id, refresh_expires)
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_expires,
            refresh_expires_at=refresh_expires,
        )

    def refresh(self, refresh_token: str, access_ttl: timedelta, refresh_ttl: timedelta) -> Optional[TokenPair]:
        stored = self.refresh_tokens.get(refresh_token)
        if not stored:
            return None
        user_id, expires_at = stored
        if datetime.utcnow() >= expires_at:
            # Expired refresh token, discard it.
            self.refresh_tokens.pop(refresh_token, None)
            return None
        return self.issue_tokens(user_id, access_ttl, refresh_ttl)

    def add_profile(self, profile: Profile) -> None:
        profile.updated_at = datetime.utcnow()
        self.profiles[profile.user_id] = profile

    def add_resume(self, resume: ResumeRecord) -> ResumeRecord:
        self.resumes[resume.id] = resume
        return resume

    def add_github_connection(self, connection: GitHubConnection) -> GitHubConnection:
        self.github_connections[connection.user_id] = connection
        return connection

    def add_application_log(self, entry: ApplicationLogEntry) -> ApplicationLogEntry:
        self.application_logs.append(entry)
        return entry


store = InMemoryStore()
