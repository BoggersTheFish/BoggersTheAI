from __future__ import annotations

import logging
import math
from typing import Dict, List

logger = logging.getLogger("boggers.embeddings")


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a < 1e-12 or mag_b < 1e-12:
        return 0.0
    return dot / (mag_a * mag_b)


def batch_cosine_matrix(
    embeddings: Dict[str, List[float]],
) -> Dict[str, Dict[str, float]]:
    ids = list(embeddings.keys())
    matrix: Dict[str, Dict[str, float]] = {}
    for i, id_a in enumerate(ids):
        matrix[id_a] = {}
        for j, id_b in enumerate(ids):
            if i == j:
                continue
            matrix[id_a][id_b] = cosine_similarity(embeddings[id_a], embeddings[id_b])
    return matrix


class OllamaEmbedder:
    def __init__(self, model: str = "nomic-embed-text") -> None:
        self.model = model
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import ollama

            ollama.embeddings(model=self.model, prompt="test")
            self._available = True
        except Exception:
            self._available = False
            logger.debug("Ollama embedder not available for model %s", self.model)
        return self._available

    def embed(self, text: str) -> List[float]:
        try:
            import ollama

            response = ollama.embeddings(model=self.model, prompt=text)
            vec = response.get("embedding", [])
            if isinstance(vec, list) and len(vec) > 0:
                return vec
        except Exception as exc:
            logger.debug("Embedding failed: %s", exc)
        return []

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]
