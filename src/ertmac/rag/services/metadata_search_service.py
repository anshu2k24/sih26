"""
Metadata Search Service
========================
Filters RAG chunks based on structured metadata fields extracted by the OCR pipeline.

Supported filters:
  - Date ranges (date_from, date_to)
  - Tags (Drilling, Maintenance, Vibration, etc.)
  - Document type
  - Identifiers (Equipment IDs, Serial Numbers)
  - Numeric measurements (when structured extraction captured them)

All filtering operates on the metadata JSONB field in rag_chunks.
"""

import logging
from datetime import date
from typing import List, Optional, Dict, Any

from ertmac.rag.models.search_result import SearchResult, ProvenanceInfo
from ertmac.rag.models.query_model import SearchFilters
from ertmac.rag.vectorstore.factory import get_vector_store

logger = logging.getLogger("ertmac.rag.services.metadata_search")


class MetadataSearchService:
    """Filters search results based on structured metadata."""

    def filter_results(
        self,
        results: List[SearchResult],
        filters: Optional[SearchFilters],
    ) -> List[SearchResult]:
        """
        Applies metadata filters to a list of search results.

        Args:
            results: Pre-retrieved search results to filter.
            filters: Filter criteria.

        Returns:
            Filtered results list.
        """
        if not filters or not results:
            return results

        filtered = results

        # Date range filter
        if filters.date_from or filters.date_to:
            filtered = self._filter_by_date(filtered, filters.date_from, filters.date_to)

        # Tag filter
        if filters.tags:
            filtered = self._filter_by_tags(filtered, filters.tags)

        # Document type filter
        if filters.document_type:
            filtered = self._filter_by_document_type(filtered, filters.document_type)

        # Identifier filter (exact match in entity_values metadata)
        if filters.identifiers:
            filtered = self._filter_by_identifiers(filtered, filters.identifiers)

        # Organization filter
        if filters.organization_id:
            filtered = [
                r for r in filtered
                if r.metadata.get("organization_id") == filters.organization_id
                or r.metadata.get("organization_id") is None  # no org = accessible to all
            ]

        return filtered

    def search_by_metadata(
        self,
        filters: SearchFilters,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Fetches all chunks and applies metadata filtering.
        Used for pure metadata-only queries.
        """
        # Get all chunks from store and filter locally
        store = get_vector_store()
        # We fetch a broad set and filter
        # For local store: iterate _chunks
        # For pgvector: this would ideally be a server-side query
        all_chunks = []

        if hasattr(store, "_chunks"):
            # LocalVectorStore
            for chunk_id, chunk_data in store._chunks.items():
                metadata = chunk_data.get("metadata", {})
                result = SearchResult(
                    note_id=chunk_data["note_id"],
                    chunk_id=chunk_id,
                    title=metadata.get("title", "Untitled"),
                    section=chunk_data.get("section", "body"),
                    text=chunk_data.get("content", ""),
                    score=1.0,
                    metadata=metadata,
                    metadata_score=1.0,
                    provenance=ProvenanceInfo(
                        note_id=chunk_data["note_id"],
                        chunk_id=chunk_id,
                    ),
                )
                all_chunks.append(result)
        else:
            logger.debug("MetadataSearchService: pgvector metadata-only search is limited without semantic query")

        filtered = self.filter_results(all_chunks, filters)
        return filtered[:top_k]

    # ── Private Filters ───────────────────────────────────────────────────

    def _filter_by_date(
        self,
        results: List[SearchResult],
        date_from: Optional[str],
        date_to: Optional[str],
    ) -> List[SearchResult]:
        """Filters by date range using metadata.date field."""
        filtered = []
        for r in results:
            doc_date_str = r.metadata.get("date") or r.metadata.get("verified_at", "")
            if not doc_date_str:
                filtered.append(r)  # No date info — include by default
                continue
            try:
                doc_date = date.fromisoformat(doc_date_str[:10])
                if date_from and doc_date < date.fromisoformat(date_from):
                    continue
                if date_to and doc_date > date.fromisoformat(date_to):
                    continue
                filtered.append(r)
            except (ValueError, TypeError):
                filtered.append(r)  # Unparseable date — include by default
        return filtered

    def _filter_by_tags(
        self,
        results: List[SearchResult],
        required_tags: List[str],
    ) -> List[SearchResult]:
        """Filters results that contain at least one of the required tags."""
        required_lower = {t.lower() for t in required_tags}
        filtered = []
        for r in results:
            doc_tags = {t.lower() for t in (r.metadata.get("tags") or [])}
            if doc_tags & required_lower:  # intersection
                filtered.append(r)
        return filtered

    def _filter_by_document_type(
        self,
        results: List[SearchResult],
        doc_type: str,
    ) -> List[SearchResult]:
        """Filters by document_type metadata field."""
        doc_type_lower = doc_type.lower()
        return [
            r for r in results
            if doc_type_lower in (r.metadata.get("document_type", "") or "").lower()
        ]

    def _filter_by_identifiers(
        self,
        results: List[SearchResult],
        identifiers: List[str],
    ) -> List[SearchResult]:
        """Filters results containing at least one of the specified identifiers."""
        id_lower = {i.lower() for i in identifiers}
        filtered = []
        for r in results:
            entity_values = {
                v.lower()
                for v in (r.metadata.get("entity_values") or [])
                if v
            }
            # Also check chunk content directly for identifiers
            content_lower = r.text.lower()
            has_id = bool(entity_values & id_lower)
            if not has_id:
                has_id = any(ident.lower() in content_lower for ident in identifiers)
            if has_id:
                filtered.append(r)
        return filtered


# Module singleton
global_metadata_search_service = MetadataSearchService()
