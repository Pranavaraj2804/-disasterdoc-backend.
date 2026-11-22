import os
import json
import faiss
import numpy as np
from typing import List, Dict, Tuple

class FAISSVectorStore:
    def __init__(self, store_dir: str = "backend/storage/faiss_index"):
        self.store_dir = store_dir
        os.makedirs(store_dir, exist_ok=True)
        self.index_path = os.path.join(store_dir, "disasterdoc.faiss")
        self.meta_path = os.path.join(store_dir, "chunks_meta.json")
        self.index = None
        self.chunks: List[Dict] = []

    def build_and_save(self, embeddings: np.ndarray, chunks: List[Dict]):
        dim = embeddings.shape[1]
        # Inner Product on L2-normalized vectors == Cosine Similarity
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)
        self.chunks = chunks

        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

    def load(self) -> bool:
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.meta_path, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)
            return True
        return False

    def search(self, query_vec: np.ndarray, top_k: int = 6) -> List[Tuple[float, Dict]]:
        if self.index is None:
            raise RuntimeError("FAISS index not loaded or built.")
        scores, indices = self.index.search(query_vec, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and idx < len(self.chunks):
                results.append((float(score), self.chunks[idx]))
        return results
