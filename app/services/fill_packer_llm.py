import json
from typing import Any, Dict, Optional

from app.services.llm_client import get_client


SYSTEM_PROMPT = """You generate concise, practical job-application autofill packets.
Return ONLY valid JSON. No markdown, no extra text.

Rules:
- Use India context unless specified.
- years_experience should be "0" for freshers unless user profile says otherwise.
- expected_salary should be "Negotiable" unless specified.
- notice_period for student/fresher: "0 days"
- work_authorization: "yes" if applying in their home country unless specified.
- visa_sponsorship: default "no" unless specified.
- relocation: default "yes" unless specified.
"""


def generate_fill_packet(
    job_description: str,
    job_title: Optional[str] = None,
    company: Optional[str] = None,
    profile: Optional[Dict[str, Any]] = None,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    client = get_client()

    payload = {
        "job_title": job_title or "",
        "company": company or "",
        "job_description": job_description or "",
        "profile": profile or {},
        "output_schema": {
            "packet": {
                "location": "string",
                "work_authorization": "yes|no",
                "visa_sponsorship": "yes|no",
                "relocation": "yes|no",
                "notice_period": "string",
                "expected_salary": "string",
                "years_experience": "string",
                "key_skills": "string",
                "summary": "string",
            },
            "screening_answers": "object mapping question->answer",
            "resume_keywords": "list of strings",
            "cover_letter_short": "string",
            "one_liner": "string",
        },
    }

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
    )

    text = resp.output_text.strip()

    # Hard-guard: must be JSON
    try:
        return json.loads(text)
    except Exception as e:
        raise RuntimeError(f"LLM did not return valid JSON. Error={e}. Raw={text[:500]}")
