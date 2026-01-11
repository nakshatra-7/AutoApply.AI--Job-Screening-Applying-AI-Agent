from typing import Dict, List

from app.services.vector_store import vector_store


class RecommendationService:
    RESUME_NS = "resume"
    PROJECT_NS = "project"
    QA_NS = "qa"

    def upsert_project_embedding(self, project_id: str, embedding: List[float], metadata: Dict):
        vector_store.upsert(self.PROJECT_NS, project_id, embedding, metadata)

    def upsert_resume_embedding(self, resume_id: str, embedding: List[float], metadata: Dict):
        vector_store.upsert(self.RESUME_NS, resume_id, embedding, metadata)

    def upsert_qa_embedding(self, qa_id: str, embedding: List[float], metadata: Dict):
        vector_store.upsert(self.QA_NS, qa_id, embedding, metadata)

    def top_projects_for_jd(self, jd_embedding: List[float], top_k: int = 3):
        return vector_store.query(self.PROJECT_NS, jd_embedding, top_k=top_k)

    def top_resume_for_jd(self, jd_embedding: List[float], top_k: int = 1):
        return vector_store.query(self.RESUME_NS, jd_embedding, top_k=top_k)

    def similar_answers(self, question_embedding: List[float], top_k: int = 3):
        return vector_store.query(self.QA_NS, question_embedding, top_k=top_k)


recommendation_service = RecommendationService()

