from collections import Counter
from typing import List, Optional

from app.models.store import store


class JobAnalysisService:
    def analyse(self, user_id: str, job_title: str, description: str, required_skills: Optional[List[str]] = None):
        if user_id not in store.users:
            return None

        profile = store.profiles.get(user_id)
        profile_skills = profile.skills if profile else []
        tokens = [token.strip(".,:;").lower() for token in description.split() if token]
        common_keywords = [word for word, _ in Counter(tokens).most_common(8)]
        required_set = set(skill.lower() for skill in required_skills or [])
        overlap = required_set.intersection(set(skill.lower() for skill in profile_skills))
        score = round((len(overlap) / max(len(required_set) or 1, 1)) * 100, 2)

        # Pick latest resume for the user as a suggestion.
        suggested_resume = None
        user_resumes = [res for res in store.resumes.values() if res.user_id == user_id]
        if user_resumes:
            suggested_resume = sorted(user_resumes, key=lambda r: r.uploaded_at, reverse=True)[0].id

        recommendations = {
            "profile": "Add a summary and location to improve matching." if not profile else "Profile found",
            "resume": "Upload a tailored resume with role keywords." if not user_resumes else "Resume ready",
        }
        return {
            "job_title": job_title,
            "keywords": common_keywords,
            "score_against_profile": score,
            "suggested_resume_id": suggested_resume,
            "recommendations": recommendations,
        }


job_analysis_service = JobAnalysisService()

