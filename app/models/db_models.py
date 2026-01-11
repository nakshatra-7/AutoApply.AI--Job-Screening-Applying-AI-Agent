from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    experiences = relationship("Experience", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="user", cascade="all, delete-orphan")
    facts = relationship("UserFact", back_populates="user", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    resume_type = Column(String(64), nullable=True)  # e.g. SDE / ML / Data
    filename = Column(String(512), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    parsed_json = Column(JSON, nullable=True)

    user = relationship("User", back_populates="resumes")
    applications = relationship(
    "Application",
    back_populates="resume",
    foreign_keys="Application.used_resume_id",
)


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    tech_stack = Column(String(512), nullable=True)
    metrics = Column(String(255), nullable=True)
    source = Column(String(64), nullable=True)  # resume/github
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="projects")


class Experience(Base):
    __tablename__ = "experiences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    tech_stack = Column(String(512), nullable=True)
    metrics = Column(String(255), nullable=True)
    source = Column(String(64), nullable=True)  # resume/github
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="experiences")


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    company = Column(String(255), nullable=False)
    job_title = Column(String(255), nullable=False)
    job_url = Column(String(1024), nullable=True)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used_resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=True)
    fit_score = Column(Float, nullable=True)
    status = Column(String(64), nullable=True)  # applied/interview/offer/rejected

    user = relationship("User", back_populates="applications")
    resume = relationship(
    "Resume",
    back_populates="applications",
    foreign_keys=[used_resume_id],
)

    answers = relationship("Answer", back_populates="application", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="application")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    char_limit = Column(Integer, nullable=True)
    edited_by_user = Column(Boolean, default=False, nullable=False)

    application = relationship("Application", back_populates="answers")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    default_tone = Column(String(64), nullable=True)
    default_resume_type = Column(String(64), nullable=True)
    default_location = Column(String(255), nullable=True)
    notification_preferences = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="settings")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    goal = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="planning")
    fit_score = Column(Float, nullable=True)
    selected_resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="agent_runs")
    steps = relationship("AgentStepLog", back_populates="run", cascade="all, delete-orphan")
    application = relationship("Application", back_populates="agent_runs")
    selected_resume = relationship("Resume")


class AgentStepLog(Base):
    __tablename__ = "agent_step_logs"

    id = Column(UUID(as_uuid=True), primary_key=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=False, index=True)
    step_num = Column(Integer, nullable=False)
    name = Column(String(64), nullable=False)
    tool = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    run = relationship("AgentRun", back_populates="steps")


class UserFact(Base):
    __tablename__ = "user_facts"

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    key = Column(String(128), nullable=False, index=True)
    value = Column(JSON, nullable=False)
    source = Column(String(64), nullable=False, default="user_confirmed")
    last_confirmed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="facts")

    __table_args__ = (
        UniqueConstraint("user_id", "key"),
    )
