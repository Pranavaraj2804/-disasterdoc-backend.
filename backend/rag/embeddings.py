import os
import numpy as np
from typing import List
from fastembed import TextEmbedding   # same MiniLM model, but ONNX (no PyTorch) so it fits in 512 MB


class EmbeddingEngine:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = TextEmbedding(
            model_name=model_name,
            cache_dir=os.environ.get("FASTEMBED_CACHE", "/app/.fastembed"),
        )

    def encode_texts(self, texts: List[str]) -> np.ndarray:
        vecs = np.array(list(self.model.embed(list(texts))), dtype="float32")
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (vecs / norms).astype("float32")
