"""
Mistral Embedding Provider
===========================
Uses Mistral AI's `mistral-embed` model for production-quality embeddings.

Model specs:
    Name:       mistral-embed
    Dimension:  1024
    Max tokens: 8192
    Quality:    High — suitable for technical / multilingual text

Configuration:
    RAG_EMBEDDING_PROVIDER=mistral
    RAG_EMBEDDING_MODEL=mistral-embed
    MISTRAL_API_KEY=your-api-key

Installation:
    pip install mistralai

Note: Requires an active internet connection and Mistral API key.
      Use sentence_transformers for offline/hackathon deployments.
"""

import logging
import os
from typing import List

from ertmac.rag.embeddings.base import EmbeddingProvider

logger = logging.getLogger("ertmac.rag.embeddings.mistral")

_MISTRAL_MODEL_DIMENSIONS = {
    "mistral-embed": 1024,
}


class MistralEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using Mistral AI's embedding API."""

    def __init__(self, model_name: str = "mistral-embed", api_key: str = None):
        self._model_name = model_name
        self._api_key = api_key or os.getenv("MISTRAL_API_KEY", "")
        self._dim = _MISTRAL_MODEL_DIMENSIONS.get(model_name, 1024)
        self._client = None

        if not self._api_key:
            logger.warning(
                "MISTRAL_API_KEY is not set. Mistral embedding provider will fail on first use."
            )

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def provider_name(self) -> str:
        return f"mistral/{self._model_name}"

    def _get_client(self):
        if self._client is None:
            try:
                from mistralai import Mistral
                if not self._api_key:
                    raise RuntimeError("MISTRAL_API_KEY is not configured")
                self._client = Mistral(api_key=self._api_key)
            except ImportError:
                raise RuntimeError(
                    "mistralai package not installed. Run: pip install mistralai"
                )
        return self._client

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        client = self._get_client()
        try:
            response = client.embeddings.create(
                model=self._model_name,
                inputs=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise RuntimeError(f"Mistral embedding API error: {e}") from e

    def health_check(self) -> bool:
        try:
            vec = self.embed_text("health check")
            return len(vec) == self._dim
        except Exception as e:
            logger.warning(f"Mistral embedding health check failed: {e}")
            return False
