"""
Embedding Provider Factory
===========================
Returns the configured EmbeddingProvider based on RAG_EMBEDDING_PROVIDER env var.

Usage:
    from ertmac.rag.embeddings.factory import get_embedding_provider
    provider = get_embedding_provider()
    vector = provider.embed_text("high vibration detected near pump")
"""

import logging
import os
from typing import Optional

from ertmac.rag.embeddings.base import EmbeddingProvider

logger = logging.getLogger("ertmac.rag.embeddings.factory")

_provider_instance: Optional[EmbeddingProvider] = None


def get_embedding_provider(force_provider: Optional[str] = None) -> EmbeddingProvider:
    """
    Returns singleton embedding provider based on RAG_EMBEDDING_PROVIDER env var.

    Supported values:
        sentence_transformers  — local, free, no API key (DEFAULT)
        mistral                — Mistral API (requires MISTRAL_API_KEY)

    Args:
        force_provider: Override env var for testing.
    """
    global _provider_instance

    if _provider_instance is not None and force_provider is None:
        return _provider_instance

    provider_name = (force_provider or os.getenv("RAG_EMBEDDING_PROVIDER", "sentence_transformers")).lower().strip()
    model_name = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    if provider_name in ("sentence_transformers", "sentence-transformers", "sbert"):
        from ertmac.rag.embeddings.sentence_transformer_provider import SentenceTransformerProvider
        instance = SentenceTransformerProvider(model_name=model_name)

    elif provider_name == "mistral":
        from ertmac.rag.embeddings.mistral_provider import MistralEmbeddingProvider
        instance = MistralEmbeddingProvider(model_name=model_name)

    else:
        logger.warning(
            f"Unknown RAG_EMBEDDING_PROVIDER='{provider_name}'. "
            f"Falling back to sentence_transformers."
        )
        from ertmac.rag.embeddings.sentence_transformer_provider import SentenceTransformerProvider
        instance = SentenceTransformerProvider()

    logger.info(f"Embedding provider initialized: {instance.provider_name} (dim={instance.dimension})")

    if force_provider is None:
        _provider_instance = instance

    return instance


def reset_embedding_provider():
    """Resets the singleton — used in tests."""
    global _provider_instance
    _provider_instance = None
