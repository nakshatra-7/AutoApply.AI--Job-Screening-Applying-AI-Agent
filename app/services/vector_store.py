from typing import Dict, List, Tuple

# Placeholder interface for vector DB operations (e.g., pgvector, Pinecone, Weaviate).
class VectorStore:
    def __init__(self):
        # In-memory stub: mapping from namespace -> list of (id, embedding, metadata)
        self.namespaces: Dict[str, List[Tuple[str, List[float], Dict]]] = {}

    def upsert(self, namespace: str, item_id: str, embedding: List[float], metadata: Dict):
        self.namespaces.setdefault(namespace, [])
        self.namespaces[namespace] = [entry for entry in self.namespaces[namespace] if entry[0] != item_id]
        self.namespaces[namespace].append((item_id, embedding, metadata))

    def query(self, namespace: str, embedding: List[float], top_k: int = 3) -> List[Dict]:
        # Very naive cosine similarity placeholder; replace with vector DB client calls.
        from math import sqrt

        def cosine(a: List[float], b: List[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sqrt(sum(x * x for x in a)) or 1.0
            norm_b = sqrt(sum(y * y for y in b)) or 1.0
            return dot / (norm_a * norm_b)

        entries = self.namespaces.get(namespace, [])
        scored = [
            {"id": item_id, "score": cosine(embedding, emb), "metadata": metadata}
            for item_id, emb, metadata in entries
        ]
        return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_k]


vector_store = VectorStore()
