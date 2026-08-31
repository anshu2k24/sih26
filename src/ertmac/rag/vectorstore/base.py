"""
Vector Store Abstract Base
===========================
All vector store backends must implement this interface.
Enables switching between pgvector (production) and local numpy fallback (development)
without modifying the retrieval services.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from ertmac.rag.models.rag_chunk import RAGChunk
from ertmac.rag.models.search_result import SearchResult


class VectorStore(ABC):
    """Abstract interface for vector storage and similarity search."""

    @abstractmethod
    def initialize(self) -> None:
        """
        Sets up any required database tables, indexes, or files.
        Must be idempotent — safe to call multiple times.
        """
        ...

    @abstractmethod
    def upsert_chunks(self, chunks: List[RAGChunk]) -> None:
        """
        Inserts or updates chunks in the vector store.
        Uses chunk.id as the upsert key when set.

        Args:
            chunks: RAGChunk objects with embeddings populated.

        Raises:
            RuntimeError: if the store is unavailable.
        """
        ...

    @abstractmethod
    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Finds the top-k chunks most similar to the query embedding.

        Args:
            query_embedding: The query vector.
            top_k: Maximum number of results to return.
            filters: Optional metadata filters (note_id, organization_id, etc.)

        Returns:
            List of SearchResult objects ordered by descending similarity score.
        """
        ...

    @abstractmethod
    def delete_by_note_id(self, note_id: str) -> int:
        """
        Removes all chunks associated with a note_id from the index.
        Does NOT delete the source note — RAG index only.

        Returns:
            Number of chunks deleted.
        """
        ...

    @abstractmethod
    def get_chunks_for_note(self, note_id: str) -> List[RAGChunk]:
        """Returns all indexed chunks for a given note_id."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Returns True if the vector store is reachable and operational."""
        ...

    @property
    @abstractmethod
    def store_name(self) -> str:
        """Human-readable store identifier for logging."""
        ...
