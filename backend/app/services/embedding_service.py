"""Embedding service — demo-mode stub (no model loading).

The sentence-transformers model takes too long to load on Docker CPU,
so for the prototype demo we skip the model entirely and return
zero-vectors.  Goal matching will return no matches (which is fine —
the intelligence pipeline still completes and actions still fire).
"""

import threading
from functools import lru_cache
from typing import List

from app.core.logging import get_logger

logger = get_logger(__name__)

# Dimensionality that matches all-MiniLM-L6-v2
_FALLBACK_DIM = 384


class EmbeddingService:
    """Stub embedding service — always returns zero-vectors.

    No model is loaded.  This lets the intelligence pipeline run to
    completion without hanging on CPU-bound model loading in Docker.
    """

    _instance: "EmbeddingService | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def _zero_vector() -> List[float]:
        return [0.0] * _FALLBACK_DIM

    async def generate_embedding(self, text: str) -> List[float]:
        """Return a zero-vector (model loading skipped for demo)."""
        logger.info("embedding_stub", text_length=len(text))
        return self._zero_vector()

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Return zero-vectors for a batch (model loading skipped)."""
        logger.info("embeddings_stub_batch", count=len(texts))
        return [self._zero_vector() for _ in texts]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Return the global EmbeddingService singleton."""
    return EmbeddingService()
