from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.fill_packet import (
    extract_keywords,
    build_packet,
    build_screening_answers,
    build_cover_letter,
    build_one_liner,
    _safe_profile,
)

router = APIRouter(prefix="/agent", tags=["agent"])


# ---- Schemas ----
class Profile(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None  # e.g., "Hyderabad, India"
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None

    # job preferences
    work_authorization: Optional[str] = None  # "yes"/"no" or country-specific
    visa_sponsorship: Optional[str] = None    # "yes"/"no"
    relocation: Optional[str] = None          # "yes"/"no"
    notice_period: Optional[str] = None       # "0 days", "2 weeks", etc.
    expected_salary: Optional[str] = None     # "₹X LPA" / "Negotiable"
    years_experience: Optional[str] = None    # "0", "1", "2" etc.

    # skills/projects (free text is fine for v1)
    skills: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)  # 3-6 bullets


class FillPacketRequest(BaseModel):
    job_url: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    job_description: str
    profile: Optional[Profile] = None
    page_url: Optional[str] = ""
    use_llm: bool = False
    llm_model: str = "gpt-5-nano"


class FillPacketResponse(BaseModel):
    packet: Dict[str, Any]
    screening_answers: Dict[str, Any]
    resume_keywords: List[str]
    cover_letter_short: str
    one_liner: str


# ---- Helpers ----
CANONICAL_FIELDS = [
    "full_name",
    "email",
    "phone",
    "location",
    "linkedin",
    "github",
    "portfolio",
    "work_authorization",
    "visa_sponsorship",
    "relocation",
    "notice_period",
    "expected_salary",
    "years_experience",
    "key_skills",
    "summary",
]

COMMON_KEYWORDS = [
    "python", "fastapi", "rest", "api", "sql", "postgres", "mysql",
    "docker", "aws", "gcp", "azure", "kubernetes",
    "react", "javascript", "typescript",
    "automation", "web scraping", "playwright", "selenium",
    "integration", "microservices", "ci/cd", "git",
]


def _safe_profile(profile: Optional[Profile]) -> Profile:
    # Minimal defaults so you get a usable packet even if profile is missing
    if profile is None:
        return Profile(
            location="India",
            work_authorization="yes",
            visa_sponsorship="no",
            relocation="yes",
            notice_period="0 days",
            expected_salary="Negotiable",
            years_experience="0",
            skills=["Python", "SQL", "APIs", "FastAPI", "Automation"],
            highlights=[
                "Built backend services and REST APIs in Python (FastAPI).",
                "Automated workflows involving web forms and data extraction.",
                "Worked with SQL databases and designed reliable data pipelines."
            ],
        )
    # Fill missing prefs with sane defaults
    return Profile(
        **{
            **profile.model_dump(),
            "work_authorization": profile.work_authorization or "yes",
            "visa_sponsorship": profile.visa_sponsorship or "no",
            "relocation": profile.relocation or "yes",
            "notice_period": profile.notice_period or "0 days",
            "expected_salary": profile.expected_salary or "Negotiable",
            "years_experience": profile.years_experience or "0",
            "location": profile.location or "India",
            "skills": profile.skills or ["Python", "SQL", "APIs", "FastAPI", "Automation"],
            "highlights": profile.highlights or [
                "Built backend services and REST APIs in Python (FastAPI).",
                "Automated workflows involving web forms and data extraction.",
                "Worked with SQL databases and designed reliable data pipelines."
            ],
        }
    )


def extract_keywords(jd: str) -> List[str]:
    text = (jd or "").lower()
    found = []
    for kw in COMMON_KEYWORDS:
        if kw in text:
            found.append(kw)
    # keep unique, stable order
    seen = set()
    out = []
    for k in found:
        if k not in seen:
            out.append(k)
            seen.add(k)
    return out


def build_cover_letter(job_title: Optional[str], company: Optional[str], profile: Profile, keywords: List[str]) -> str:
    jt = job_title or "Software Engineer"
    co = company or "your team"
    top = ", ".join([k for k in keywords[:6]]) if keywords else "backend, APIs, and automation"

    bullets = profile.highlights[:3]
    bullets_txt = "\n".join([f"- {b}" for b in bullets])

    return (
        f"Hi {co},\n\n"
        f"I’m applying for the {jt} role. I work primarily in Python and enjoy building backend systems that are reliable and practical.\n"
        f"My recent work aligns with what you need: {top}.\n\n"
        f"{bullets_txt}\n\n"
        f"I can start with {profile.notice_period} notice, and I’m happy to share more details or a quick demo.\n"
        f"Thanks,\n"
        f"{profile.full_name or 'Candidate'}"
    )


def build_one_liner(job_title: Optional[str], profile: Profile, keywords: List[str]) -> str:
    jt = job_title or "SWE"
    top = ", ".join([k for k in keywords[:4]]) if keywords else "Python, APIs, SQL, automation"
    return f"{jt} candidate focused on {top}; comfortable shipping backend features and automation end-to-end."


def build_packet(req: FillPacketRequest) -> Dict[str, Any]:
    profile = _safe_profile(req.profile)
    keywords = extract_keywords(req.job_description)

    key_skills = profile.skills
    # Add keywords from JD to skill list (lightly) without duplicates
    for k in keywords[:10]:
        # keep human readable casing for common skills
        pretty = k.upper() if k in {"sql", "api", "ci/cd"} else k.title()
        if pretty not in key_skills and k not in [s.lower() for s in key_skills]:
            key_skills.append(pretty)

    summary = build_one_liner(req.job_title, profile, keywords)

    packet = {
        "full_name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "location": profile.location,
        "linkedin": profile.linkedin,
        "github": profile.github,
        "portfolio": profile.portfolio,
        "work_authorization": profile.work_authorization,
        "visa_sponsorship": profile.visa_sponsorship,
        "relocation": profile.relocation,
        "notice_period": profile.notice_period,
        "expected_salary": profile.expected_salary,
        "years_experience": profile.years_experience,
        "key_skills": ", ".join(key_skills),
        "summary": summary,
        "job_url": req.job_url,
        "job_title": req.job_title,
        "company": req.company,
    }

    # drop None values to keep it clean
    packet = {k: v for k, v in packet.items() if v is not None}
    return packet


def build_screening_answers(packet: Dict[str, Any]) -> Dict[str, Any]:
    # Normalized, portal-friendly answers
    def yn(v: Any) -> str:
        s = str(v or "").strip().lower()
        if s in {"yes", "y", "true", "1"}:
            return "Yes"
        if s in {"no", "n", "false", "0"}:
            return "No"
        return str(v) if v is not None else ""

    return {
        "Work authorization?": yn(packet.get("work_authorization")),
        "Need visa sponsorship?": yn(packet.get("visa_sponsorship")),
        "Open to relocation?": yn(packet.get("relocation")),
        "Notice period": packet.get("notice_period", ""),
        "Expected salary": packet.get("expected_salary", ""),
        "Years of experience": packet.get("years_experience", ""),
        "Location": packet.get("location", ""),
        "LinkedIn": packet.get("linkedin", ""),
        "GitHub": packet.get("github", ""),
        "Portfolio": packet.get("portfolio", ""),
    }


@router.post("/fill_packet", response_model=FillPacketResponse)
def fill_packet(req: FillPacketRequest) -> FillPacketResponse:
    keywords = extract_keywords(req.job_description)
    profile = _safe_profile(req.profile)

    packet = build_packet(req)
    screening = build_screening_answers(packet)
    cover = build_cover_letter(req.job_title, req.company, profile, keywords)
    one_liner = build_one_liner(req.job_title, profile, keywords)

    return FillPacketResponse(
        packet=packet,
        screening_answers=screening,
        resume_keywords=keywords,
        cover_letter_short=cover,
        one_liner=one_liner,
    )
