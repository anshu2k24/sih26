"""
Sentence Transformers Embedding Provider
=========================================
Uses the `sentence-transformers` library with the all-MiniLM-L6-v2 model.

Model specs:
    Name:       all-MiniLM-L6-v2
    Dimension:  384
    Max tokens: 256 (longer texts are automatically truncated)
    License:    Apache 2.0
    Size:       ~90MB (downloaded on first use, cached locally)

Installation:
    pip install sentence-transformers

Configuration:
    RAG_EMBEDDING_PROVIDER=sentence_transformers
    RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2  (or any other SBERT model)
"""

import logging
import os
from typing import List, Optional

from ertmac.rag.embeddings.base import EmbeddingProvider

logger = logging.getLogger("ertmac.rag.embeddings.sentence_transformers")

_DIMENSION_MAP = {
    "all-MiniLM-L6-v2": 384,
    "all-MiniLM-L12-v2": 384,
    "all-mpnet-base-v2": 768,
    "paraphrase-multilingual-MiniLM-L12-v2": 384,
}


class SentenceTransformerProvider(EmbeddingProvider):
    """
    Local embedding provider using sentence-transformers.
    Model is lazy-loaded on first use and cached for subsequent calls.
    """

    def __init__(self, model_name: Optional[str] = None):
        self._model_name = model_name or os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self._model = None  # Lazy load
        self._dim = _DIMENSION_MAP.get(self._model_name, 384)

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def provider_name(self) -> str:
        return f"sentence_transformers/{self._model_name}"

    def _get_model(self):
        """Lazy-loads the model on first use."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading sentence-transformers model: {self._model_name}")
                self._model = SentenceTransformer(self._model_name)
                logger.info(f"Model loaded successfully. Dimension: {self._dim}")
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers is not installed. "
                    "Run: pip install sentence-transformers"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to load model '{self._model_name}': {e}")
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single text string."""
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")
        model = self._get_model()
        try:
            vector = model.encode(text, convert_to_numpy=True)
            return vector.tolist()
        except Exception as e:
            raise RuntimeError(f"Embedding failed: {e}") from e

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch embeds multiple texts efficiently."""
        if not texts:
            return []
        # Filter empties — preserve positions for valid texts
        non_empty = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        if not non_empty:
            raise ValueError("All texts in batch are empty")

        model = self._get_model()
        try:
            indices, valid_texts = zip(*non_empty)
            batch_size = int(os.getenv("RAG_EMBEDDING_BATCH_SIZE", "32"))
            vectors = model.encode(
                list(valid_texts),
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            # Reconstruct full list preserving order
            result = [[0.0] * self._dim] * len(texts)
            for idx, vec in zip(indices, vectors):
                result[idx] = vec.tolist()
            return result
        except Exception as e:
            raise RuntimeError(f"Batch embedding failed: {e}") from e

    def health_check(self) -> bool:
        """Tests the model with a simple probe sentence."""
        try:
            vec = self.embed_text("health check probe")
            return len(vec) == self._dim
        except Exception as e:
            logger.warning(f"Embedding health check failed: {e}")
            return False
