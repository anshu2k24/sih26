"""
Keyword Search Service
=======================
Exact and full-text keyword search over indexed RAG chunks.

Critical for:
  - Equipment IDs: MUD-PUMP-008
  - Serial numbers: SN XR-8829
  - Dates: 2026-08-31
  - Technical identifiers that must not rely on vector similarity

Implementation:
  - pgvector store: PostgreSQL ts_vector / plainto_tsquery
  - local store: Python token matching fallback
"""

import logging
from typing import List, Optional, Dict, Any

from ertmac.rag.models.search_result import SearchResult
from ertmac.rag.models.query_model import SearchFilters
from ertmac.rag.vectorstore.factory import get_vector_store

logger = logging.getLogger("ertmac.rag.services.keyword_search")


class KeywordSearchService:
    """Full-text and exact identifier search."""

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[SearchFilters] = None,
    ) -> List[SearchResult]:
        """
        Performs keyword/full-text search over indexed chunks.

        Args:
            query: Search string.
            top_k: Maximum results.
            filters: Optional metadata filters.

        Returns:
            List of SearchResult ordered by relevance score.
        """
        query = query.strip()
        if not query:
            return []

        store = get_vector_store()
        filter_dict = filters.to_dict() if filters else {}

        try:
            if hasattr(store, "fulltext_search"):
                results = store.fulltext_search(query=query, top_k=top_k, filters=filter_dict)
            else:
                # Fallback: local store has fulltext_search too
                results = store.fulltext_search(query=query, top_k=top_k, filters=filter_dict)

            logger.debug(f"KeywordSearch '{query}': {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"KeywordSearchService error: {e}")
            return []


# Module singleton
global_keyword_search_service = KeywordSearchService()
