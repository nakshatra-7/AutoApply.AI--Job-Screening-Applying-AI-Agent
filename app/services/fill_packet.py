from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def extract_keywords(job_description: str, max_keywords: int = 12) -> List[str]:
    """
    Tiny keyword extractor: deterministic + fast.
    You can replace later with LLM or better NLP.
    """
    text = (job_description or "").lower()

    # keep words only
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\+\#\.\-]{1,}", text)

    stop = {
        "and", "or", "the", "a", "an", "to", "of", "in", "for", "with", "on", "as",
        "is", "are", "be", "will", "you", "we", "our", "your", "this", "that",
        "role", "job", "skills", "years", "experience", "strong", "good", "nice",
    }

    # lightweight scoring: keep unique meaningful tokens
    uniq: List[str] = []
    seen = set()
    for w in words:
        w = w.strip().lower()
        if w in stop:
            continue
        if len(w) < 3:
            continue
        if w in seen:
            continue
        seen.add(w)
        uniq.append(w)

    # prioritize common SWE terms if present
    priority = [
        "python", "sql", "api", "apis", "fastapi", "backend", "automation",
        "rest", "restful", "docker", "aws", "cloud", "javascript", "react",
        "workday", "playwright",
    ]
    ordered: List[str] = []
    for p in priority:
        if p in seen and p not in ordered:
            ordered.append(p)

    # fill remaining
    for w in uniq:
        if w not in ordered:
            ordered.append(w)

    return ordered[:max_keywords]


def _safe_profile(profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return profile or {}


def build_packet(req) -> Dict[str, str]:
    """
    Produces a canonical packet of common screening fields.
    `req` is your FillPacketRequest (pydantic model) from app/api/fill_packet.py
    """
    job_desc = getattr(req, "job_description", "") or ""
    keywords = extract_keywords(job_desc)

    # Defaults (edit to your preference)
    location = "India"
    work_auth = "yes"
    visa = "no"
    relocation = "yes"
    notice = "0 days"
    salary = "Negotiable"
    yoe = "0"

    # try to use provided profile fields if any
    profile = _safe_profile(getattr(req, "profile", None))
    location = profile.get("location") or location
    yoe = str(profile.get("years_experience") or yoe)

    # Skill line
    skills = profile.get("skills")
    if isinstance(skills, list) and skills:
        key_skills = ", ".join(map(str, skills))
    else:
        # make it readable
        pretty = []
        for k in keywords[:8]:
            pretty.append(k.upper() if k in {"sql", "api", "apis"} else k.capitalize())
        key_skills = ", ".join(pretty) if pretty else "Python, SQL, APIs"

    return {
        "location": str(location),
        "work_authorization": str(work_auth),
        "visa_sponsorship": str(visa),
        "relocation": str(relocation),
        "notice_period": str(notice),
        "expected_salary": str(salary),
        "years_experience": str(yoe),
        "key_skills": str(key_skills),
        "summary": build_one_liner(getattr(req, "job_title", None), profile, keywords),
    }


def build_screening_answers(packet: Dict[str, str]) -> Dict[str, str]:
    # Typical mapping you can feed to your extension/UI
    return {
        "Work authorization?": "Yes" if packet.get("work_authorization", "").lower() == "yes" else "No",
        "Need visa sponsorship?": "Yes" if packet.get("visa_sponsorship", "").lower() == "yes" else "No",
        "Open to relocation?": "Yes" if packet.get("relocation", "").lower() == "yes" else "No",
        "Notice period": packet.get("notice_period", ""),
        "Expected salary": packet.get("expected_salary", ""),
        "Years of experience": packet.get("years_experience", ""),
        "Location": packet.get("location", ""),
        "LinkedIn": "",
        "GitHub": "",
        "Portfolio": "",
    }


def build_cover_letter(job_title: Optional[str], company: Optional[str], profile: Dict[str, Any], keywords: List[str]) -> str:
    title = job_title or "Software Engineer"
    comp = company or "your team"
    top = ", ".join(keywords[:3]) if keywords else "backend development"

    return (
        f"Hi {comp},\n\n"
        f"I’m applying for the {title} role. I work primarily in Python and enjoy building backend systems "
        f"that are reliable and practical.\n"
        f"My recent work aligns with what you need: {top}.\n\n"
        f"- Built backend services and REST APIs in Python (FastAPI).\n"
        f"- Automated workflows involving web forms and data extraction.\n"
        f"- Worked with SQL databases and designed reliable data pipelines.\n\n"
        f"I can start with {profile.get('notice_period', '0 days')} notice, and I’m happy to share more details or a quick demo.\n"
        f"Thanks,\n"
        f"Candidate"
    )


def build_one_liner(job_title: Optional[str], profile: Dict[str, Any], keywords: List[str]) -> str:
    top = ", ".join(keywords[:3]) if keywords else "backend, APIs, SQL"
    title = job_title or "SWE"
    return f"{title} candidate focused on {top}; comfortable shipping backend features and automation end-to-end."
