"""
Semantic Search Service
========================
Embeds the user query and retrieves semantically similar chunks via vector similarity.

Example:
    Query: "machine shaking"
    Retrieves: "high vibration detected near mud pump"

    Query: "fluid escaping from pipe"
    Retrieves: "oil leakage observed near valve assembly"
"""

import logging
from typing import List, Optional

from ertmac.rag.models.search_result import SearchResult
from ertmac.rag.models.query_model import SearchFilters
from ertmac.rag.services.embedding_service import global_embedding_service, EmbeddingService
from ertmac.rag.vectorstore.factory import get_vector_store

logger = logging.getLogger("ertmac.rag.services.semantic_search")


class SemanticSearchService:
    """Vector similarity search over RAG chunks."""

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self._embedder = embedding_service or global_embedding_service

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[SearchFilters] = None,
    ) -> List[SearchResult]:
        """
        Embeds the query and performs vector similarity search.

        Args:
            query: Natural language search string.
            top_k: Maximum results.
            filters: Optional metadata filters.

        Returns:
            List of SearchResult ordered by descending semantic similarity.
        """
        query = query.strip()
        if not query:
            return []

        # Step 1: Embed query
        try:
            query_embedding = self._embedder.embed_query(query)
        except Exception as e:
            logger.error(f"SemanticSearchService: Query embedding failed: {e}")
            return []

        # Step 2: Vector similarity search
        store = get_vector_store(embedding_dim=self._embedder.dimension)
        filter_dict = filters.to_dict() if filters else {}

        try:
            results = store.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k,
                filters=filter_dict,
            )
            logger.debug(f"SemanticSearch '{query}': {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"SemanticSearchService: similarity_search failed: {e}")
            return []


# Module singleton
global_semantic_search_service = SemanticSearchService()
