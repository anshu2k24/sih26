"""
Embedding Service
==================
Wraps the embedding provider with batch processing, error handling,
and dimension validation. All RAG services access embeddings through this layer.
"""

import logging
import os
from typing import List, Optional

from ertmac.rag.embeddings.factory import get_embedding_provider
from ertmac.rag.models.rag_chunk import RAGChunk

logger = logging.getLogger("ertmac.rag.services.embedding")


class EmbeddingService:
    """Manages embedding generation for RAG chunks and queries."""

    def __init__(self, provider=None):
        self._provider = provider  # None → lazy init from factory

    def _get_provider(self):
        if self._provider is None:
            self._provider = get_embedding_provider()
        return self._provider

    @property
    def dimension(self) -> int:
        return self._get_provider().dimension

    def embed_query(self, query: str) -> List[float]:
        """
        Embeds a search query into a vector.

        Args:
            query: Non-empty search string.

        Returns:
            Embedding vector.

        Raises:
            ValueError: If query is empty.
            RuntimeError: If embedding provider fails.
        """
        query = query.strip()
        if not query:
            raise ValueError("Search query cannot be empty")
        try:
            return self._get_provider().embed_text(query)
        except Exception as e:
            logger.error(f"EmbeddingService: Failed to embed query: {e}")
            raise RuntimeError(f"Embedding failed: {e}") from e

    def embed_chunks(self, chunks: List[RAGChunk]) -> List[RAGChunk]:
        """
        Embeds a list of chunks in batches.
        Modifies chunks in-place by setting the embedding field.

        Args:
            chunks: List of RAGChunk objects with non-empty content.

        Returns:
            The same list with embeddings populated.
        """
        if not chunks:
            return chunks

        batch_size = int(os.getenv("RAG_EMBEDDING_BATCH_SIZE", "32"))
        provider = self._get_provider()

        for batch_start in range(0, len(chunks), batch_size):
            batch = chunks[batch_start:batch_start + batch_size]
            texts = [c.content for c in batch]

            try:
                embeddings = provider.embed_texts(texts)
                for chunk, emb in zip(batch, embeddings):
                    chunk.embedding = emb
            except Exception as e:
                logger.error(
                    f"EmbeddingService: Batch embedding failed (start={batch_start}): {e}"
                )
                raise RuntimeError(f"Batch embedding failed: {e}") from e

        return chunks

    def health_check(self) -> bool:
        """Tests the embedding provider."""
        try:
            return self._get_provider().health_check()
        except Exception as e:
            logger.warning(f"EmbeddingService health check failed: {e}")
            return False


# Module singleton
global_embedding_service = EmbeddingService()
