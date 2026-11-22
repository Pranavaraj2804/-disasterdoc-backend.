import re
from typing import List, Dict
from backend.rag.embeddings import EmbeddingEngine
from backend.rag.vector_store import FAISSVectorStore

class SemanticRetriever:
    def __init__(self, embedder: EmbeddingEngine, vector_store: FAISSVectorStore):
        self.embedder = embedder
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 6) -> List[Dict]:
        q_low = query.lower()
        sub_queries = [query]

        if re.search(r'\b(house|houses|home|pucca|kutcha|hut|shed)\b', q_low):
            sub_queries.append("fully damaged partially damaged house pucca kutcha plain hilly hut Rs. 1,20,000 Rs. 6,500")
        if re.search(r'\b(hectare|ha|crop|paddy|farm|agriculture|agri|silt|banana|coconut|rainfed)\b', q_low):
            sub_queries.append("input subsidy paddy irrigated rainfed perennial Rs. 17,000 Rs. 8,500 Rs. 22,500 ceiling 2 hectares")
        if re.search(r'\b(died|death|deceased|loss of life|person)\b', q_low):
            sub_queries.append("ex-gratia payment families of deceased persons loss of human life Rs. 4,00,000")

        per_k = max(2, top_k // len(sub_queries))
        seen_ids = set()
        retrieved = []

        for sq in sub_queries:
            q_vec = self.embedder.encode_texts([sq])
            hits = self.vector_store.search(q_vec, top_k=per_k + 2)
            for score, chunk in hits:
                if chunk["chunk_id"] not in seen_ids:
                    seen_ids.add(chunk["chunk_id"])
                    # Boost structured G.O. 579 JSON rule tables slightly for precision
                    boosted_score = score + 0.08 if chunk["source"].endswith(".json") else score
                    retrieved.append({
                        "similarity_score": round(min(1.0, boosted_score), 4),
                        "raw_similarity": round(score, 4),
                        "chunk": chunk
                    })

        retrieved.sort(key=lambda x: x["similarity_score"], reverse=True)
        return retrieved[:top_k]
