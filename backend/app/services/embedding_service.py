"""Singleton embedding service using sentence-transformers.

Loads the model once on first use and keeps it in memory for the
lifetime of the process.  All public methods are async-safe by
offloading CPU-bound encoding to a thread executor so the FastAPI
event loop is never blocked.
"""

import asyncio
import threading
from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EmbeddingService:
    """Thread-safe singleton that generates normalised sentence embeddings.

    The underlying ``SentenceTransformer`` model is loaded lazily on the
    first call to :meth:`generate_embedding` and reused thereafter.
    """

    _instance: "EmbeddingService | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "EmbeddingService":
        """Ensure only one instance of EmbeddingService exists."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._model = None  # type: ignore[attr-defined]
        return cls._instance

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def _load_model(self) -> SentenceTransformer:
        """Load the sentence-transformer model into memory.

        Called once, guarded by the singleton pattern.

        Returns:
            The loaded SentenceTransformer model.
        """
        if self._model is None:
            model_name = settings.embedding_model
            logger.info("embedding_model_loading", model=model_name)
            self._model = SentenceTransformer(model_name)
            logger.info("embedding_model_loaded", model=model_name)
        return self._model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate a normalised 384-dimensional embedding for *text*.

        The CPU-bound encoding is executed in a thread executor so the
        async event loop is not blocked.

        Args:
            text: The input string to embed.

        Returns:
            A list of 384 floats (L2-normalised).
        """
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(None, self._encode_sync, text)
        logger.info("embedding_generated", text_length=len(text), dimensions=len(embedding))
        return embedding

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate normalised embeddings for multiple texts in one batch.

        Args:
            texts: A list of input strings.

        Returns:
            A list of embedding vectors, one per input string.
        """
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(None, self._encode_batch_sync, texts)
        logger.info("embeddings_batch_generated", count=len(texts))
        return embeddings

    # ------------------------------------------------------------------
    # Synchronous helpers (run inside executor)
    # ------------------------------------------------------------------

    def _encode_sync(self, text: str) -> List[float]:
        """Synchronously encode a single text string.

        Args:
            text: The input text.

        Returns:
            Normalised embedding as a plain Python list of floats.
        """
        model = self._load_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def _encode_batch_sync(self, texts: List[str]) -> List[List[float]]:
        """Synchronously encode multiple texts in a single forward pass.

        Args:
            texts: List of input strings.

        Returns:
            List of normalised embedding vectors.
        """
        model = self._load_model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Return the global EmbeddingService singleton.

    Returns:
        The shared EmbeddingService instance.
    """
    return EmbeddingService()
