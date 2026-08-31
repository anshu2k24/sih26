"""
Hybrid Search Service
======================
Orchestrates semantic + keyword + metadata search into a single ranked result set.

Architecture:
    User Query
          ↓
    Query Analysis
          ↓
    ┌─────────────────┬──────────────────┬──────────────────┐
    │                 │                  │                  │
    ▼                 ▼                  ▼                  ▼
  Semantic          Keyword           Metadata           Filters
  Search            Search            Matching
    │                 │                  │
    └─────────────────┴──────────────────┘
                      ↓
               Score Normalization
                      ↓
                Hybrid Ranking
                      ↓
              Duplicate Reduction
                      ↓
              Provenance Enrichment
                      ↓
              Relevant Documents

Scoring:
    hybrid_score = (semantic_score * semantic_weight) + (keyword_score * keyword_weight)
    Configurable weights via RAG_HYBRID_SEMANTIC_WEIGHT and RAG_HYBRID_KEYWORD_WEIGHT.
"""

import logging
import os
import time
from typing import List, Optional, Dict

from ertmac.rag.models.search_result import SearchResult
from ertmac.rag.models.query_model import SearchQuery, SearchFilters
from ertmac.rag.services.semantic_search_service import global_semantic_search_service, SemanticSearchService
from ertmac.rag.services.keyword_search_service import global_keyword_search_service, KeywordSearchService
from ertmac.rag.services.metadata_search_service import global_metadata_search_service, MetadataSearchService
from ertmac.rag.adapters.provenance_adapter import global_provenance_adapter, ProvenanceAdapter
from ertmac.rag.repositories.rag_audit_repository import global_rag_audit_repository, RAGAuditEvent

logger = logging.getLogger("ertmac.rag.services.hybrid_search")


class HybridSearchService:
    """
    Combines semantic, keyword, and metadata search into unified ranked results.
    This is the primary search entry point for the RAG system.
    """

    def __init__(
        self,
        semantic_service: Optional[SemanticSearchService] = None,
        keyword_service: Optional[KeywordSearchService] = None,
        metadata_service: Optional[MetadataSearchService] = None,
        provenance_adapter: Optional[ProvenanceAdapter] = None,
    ):
        self._semantic = semantic_service or global_semantic_search_service
        self._keyword = keyword_service or global_keyword_search_service
        self._metadata = metadata_service or global_metadata_search_service
        self._provenance = provenance_adapter or global_provenance_adapter

        self._default_semantic_weight = float(
            os.getenv("RAG_HYBRID_SEMANTIC_WEIGHT", "0.6")
        )
        self._default_keyword_weight = float(
            os.getenv("RAG_HYBRID_KEYWORD_WEIGHT", "0.4")
        )

    def search(
        self,
        query: SearchQuery,
        user_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Executes hybrid search.

        Args:
            query: Full search request including text, filters, weights.
            user_id: For audit logging.

        Returns:
            Deduplicated, ranked list of SearchResult objects.
        """
        start_time = time.time()
        q = query.query.strip()
        if not q:
            return []

        top_k = query.top_k
        filters = query.filters
        sem_weight = query.semantic_weight or self._default_semantic_weight
        kw_weight = query.keyword_weight or self._default_keyword_weight

        # ── Retrieve from all sources in parallel (synchronous) ───────────
        semantic_results: List[SearchResult] = []
        keyword_results: List[SearchResult] = []

        # Semantic search
        try:
            semantic_results = self._semantic.search(
                query=q, top_k=top_k * 2, filters=filters
            )
        except Exception as e:
            logger.warning(f"HybridSearch: Semantic search failed: {e}")

        # Keyword search
        try:
            keyword_results = self._keyword.search(
                query=q, top_k=top_k * 2, filters=filters
            )
        except Exception as e:
            logger.warning(f"HybridSearch: Keyword search failed: {e}")

        # ── Merge and score ────────────────────────────────────────────────
        merged = self._merge_results(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            sem_weight=sem_weight,
            kw_weight=kw_weight,
        )

        # ── Apply metadata filters ─────────────────────────────────────────
        if filters and (filters.date_from or filters.date_to or filters.tags
                        or filters.identifiers or filters.document_type):
            merged = self._metadata.filter_results(merged, filters)

        # ── Deduplicate by chunk_id ────────────────────────────────────────
        merged = self._deduplicate(merged)

        # ── Sort by hybrid score ───────────────────────────────────────────
        merged.sort(key=lambda r: r.score, reverse=True)
        final = merged[:top_k]

        # ── Enrich with provenance ────────────────────────────────────────
        for result in final:
            if result.provenance and not result.provenance.verified_at:
                result.provenance = self._provenance.build_provenance(
                    note_id=result.note_id,
                    chunk_id=result.chunk_id,
                )

        duration_ms = (time.time() - start_time) * 1000
        global_rag_audit_repository.log(
            RAGAuditEvent.SEARCH,
            user_id=user_id,
            duration_ms=duration_ms,
            metadata={
                "query": q[:100],
                "results": len(final),
                "semantic_count": len(semantic_results),
                "keyword_count": len(keyword_results),
            },
        )

        logger.info(
            f"HybridSearch '{q[:60]}': {len(final)} results "
            f"(sem={len(semantic_results)}, kw={len(keyword_results)}, {duration_ms:.0f}ms)"
        )
        return final

    # ── Private Helpers ───────────────────────────────────────────────────

    def _merge_results(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        sem_weight: float,
        kw_weight: float,
    ) -> List[SearchResult]:
        """
        Normalizes and combines semantic and keyword scores.
        Uses min-max normalization per source, then weighted combination.
        """
        # Build lookup by chunk_id
        combined: Dict[str, SearchResult] = {}

        # Normalize semantic scores
        sem_max = max((r.score for r in semantic_results), default=1.0) or 1.0
        for r in semantic_results:
            normalized_sem = r.score / sem_max
            r.semantic_score = normalized_sem
            r.score = normalized_sem * sem_weight
            combined[r.chunk_id] = r

        # Normalize keyword scores and merge
        kw_max = max((r.score for r in keyword_results), default=1.0) or 1.0
        for r in keyword_results:
            normalized_kw = r.score / kw_max
            if r.chunk_id in combined:
                # Both semantic and keyword found this chunk — combine scores
                existing = combined[r.chunk_id]
                existing.keyword_score = normalized_kw
                existing.score += normalized_kw * kw_weight
            else:
                r.keyword_score = normalized_kw
                r.score = normalized_kw * kw_weight
                combined[r.chunk_id] = r

        return list(combined.values())

    def _deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Removes duplicate chunks by chunk_id.
        Within duplicate chunk_ids, keeps the one with highest score.
        """
        seen: Dict[str, SearchResult] = {}
        for r in results:
            if r.chunk_id not in seen or r.score > seen[r.chunk_id].score:
                seen[r.chunk_id] = r
        return list(seen.values())


# Module singleton
global_hybrid_search_service = HybridSearchService()
