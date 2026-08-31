"""
Tests: RAG Retrieval Services
================================
Verifies semantic, keyword, hybrid, and metadata search with mock vector stores.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import List

from ertmac.rag.models.search_result import SearchResult, ProvenanceInfo
from ertmac.rag.models.query_model import SearchQuery, SearchFilters, SearchMode
from ertmac.rag.services.semantic_search_service import SemanticSearchService
from ertmac.rag.services.keyword_search_service import KeywordSearchService
from ertmac.rag.services.hybrid_search_service import HybridSearchService
from ertmac.rag.services.metadata_search_service import MetadataSearchService
from ertmac.rag.services.embedding_service import EmbeddingService


# ── Fixtures ──────────────────────────────────────────────────────────────

def make_result(
    note_id="note-001",
    chunk_id="chunk-001",
    title="Daily Report",
    section="observations",
    text="High vibration detected near mud pump",
    score=0.9,
    metadata=None,
    tags=None,
    date="2026-08-31",
):
    m = metadata or {}
    if tags:
        m["tags"] = tags
    if date:
        m["date"] = date
    return SearchResult(
        note_id=note_id,
        chunk_id=chunk_id,
        title=title,
        section=section,
        text=text,
        score=score,
        metadata=m,
        provenance=ProvenanceInfo(
            note_id=note_id,
            chunk_id=chunk_id,
            verified_at="2026-08-31T10:00:00Z",
            source_file_id="file-001",
        ),
    )


def make_mock_embedder(dimension=384):
    embedder = MagicMock(spec=EmbeddingService)
    embedder.dimension = dimension
    embedder.embed_query.return_value = [0.1] * dimension
    return embedder


def make_mock_store(semantic_results=None, keyword_results=None):
    store = MagicMock()
    store.similarity_search.return_value = semantic_results or []
    store.fulltext_search.return_value = keyword_results or []
    store.health_check.return_value = True
    return store


# ── Semantic Search Tests ──────────────────────────────────────────────────

class TestSemanticSearchService:

    def test_returns_results_when_store_has_matches(self):
        """Semantic search should return results from the vector store."""
        expected = [make_result(score=0.92)]
        embedder = make_mock_embedder()
        store = make_mock_store(semantic_results=expected)

        service = SemanticSearchService(embedding_service=embedder)
        with patch("ertmac.rag.services.semantic_search_service.get_vector_store", return_value=store):
            results = service.search(query="machine shaking")

        assert len(results) == 1
        assert results[0].note_id == "note-001"
        embedder.embed_query.assert_called_once_with("machine shaking")

    def test_empty_query_returns_no_results(self):
        """Empty query should return empty list without calling the store."""
        embedder = make_mock_embedder()
        store = make_mock_store()
        service = SemanticSearchService(embedding_service=embedder)

        with patch("ertmac.rag.services.semantic_search_service.get_vector_store", return_value=store):
            results = service.search(query="   ")

        assert results == []
        embedder.embed_query.assert_not_called()

    def test_embedding_failure_returns_empty_list(self):
        """If embedding fails, should return empty list without crashing."""
        embedder = MagicMock(spec=EmbeddingService)
        embedder.dimension = 384
        embedder.embed_query.side_effect = RuntimeError("Provider offline")

        service = SemanticSearchService(embedding_service=embedder)
        with patch("ertmac.rag.services.semantic_search_service.get_vector_store"):
            results = service.search(query="test query")

        assert results == []

    def test_top_k_is_respected(self):
        """top_k parameter should be passed to the vector store."""
        embedder = make_mock_embedder()
        store = make_mock_store(semantic_results=[make_result() for _ in range(3)])

        service = SemanticSearchService(embedding_service=embedder)
        with patch("ertmac.rag.services.semantic_search_service.get_vector_store", return_value=store):
            service.search(query="vibration", top_k=5)

        call_kwargs = store.similarity_search.call_args
        assert call_kwargs.kwargs.get("top_k") == 5 or (call_kwargs.args and call_kwargs.args[1] == 5)


# ── Keyword Search Tests ───────────────────────────────────────────────────

class TestKeywordSearchService:

    def test_returns_keyword_results(self):
        """Keyword search should return results matching exact terms."""
        expected = [make_result(text="MUD-PUMP-008 showing elevated vibration", score=0.85)]
        store = make_mock_store(keyword_results=expected)

        service = KeywordSearchService()
        with patch("ertmac.rag.services.keyword_search_service.get_vector_store", return_value=store):
            results = service.search(query="MUD-PUMP-008")

        assert len(results) == 1
        assert "MUD-PUMP-008" in results[0].text

    def test_empty_query_returns_empty(self):
        service = KeywordSearchService()
        results = service.search(query="")
        assert results == []


# ── Metadata Filtering Tests ───────────────────────────────────────────────

class TestMetadataSearchService:

    def test_date_filter_includes_in_range(self):
        """Results within date range should be included."""
        results = [
            make_result(note_id="note-001", date="2026-08-15"),
            make_result(note_id="note-002", date="2026-09-01"),
        ]
        filters = SearchFilters(date_from="2026-08-01", date_to="2026-08-31")
        service = MetadataSearchService()
        filtered = service.filter_results(results, filters)
        ids = [r.note_id for r in filtered]
        assert "note-001" in ids
        assert "note-002" not in ids

    def test_date_filter_includes_missing_dates(self):
        """Results with no date metadata should pass through filters by default."""
        results = [make_result(note_id="note-nodates", date=None)]
        for r in results:
            r.metadata.pop("date", None)
        filters = SearchFilters(date_from="2026-08-01", date_to="2026-08-31")
        service = MetadataSearchService()
        filtered = service.filter_results(results, filters)
        assert len(filtered) == 1

    def test_tag_filter_matches(self):
        """Results with matching tags should be included."""
        results = [
            make_result(note_id="note-maint", tags=["Maintenance", "Vibration"]),
            make_result(note_id="note-other", tags=["Geology"]),
        ]
        filters = SearchFilters(tags=["Vibration"])
        service = MetadataSearchService()
        filtered = service.filter_results(results, filters)
        assert any(r.note_id == "note-maint" for r in filtered)
        assert not any(r.note_id == "note-other" for r in filtered)

    def test_identifier_filter_matches_entity_values(self):
        """Identifier filter should match entity_values in metadata."""
        results = [
            make_result(
                note_id="note-pump",
                metadata={"entity_values": ["MUD-PUMP-008"], "tags": []},
            ),
            make_result(
                note_id="note-other",
                metadata={"entity_values": ["WELL-001"], "tags": []},
            ),
        ]
        filters = SearchFilters(identifiers=["MUD-PUMP-008"])
        service = MetadataSearchService()
        filtered = service.filter_results(results, filters)
        assert any(r.note_id == "note-pump" for r in filtered)
        assert not any(r.note_id == "note-other" for r in filtered)

    def test_identifier_filter_matches_content(self):
        """Identifier filter should also check chunk content text."""
        results = [
            make_result(
                note_id="note-content",
                text="Equipment MUD-PUMP-008 requires immediate inspection",
                metadata={"entity_values": [], "tags": []},
            ),
        ]
        filters = SearchFilters(identifiers=["MUD-PUMP-008"])
        service = MetadataSearchService()
        filtered = service.filter_results(results, filters)
        assert len(filtered) == 1


# ── Hybrid Search Tests ────────────────────────────────────────────────────

class TestHybridSearchService:

    def test_combines_semantic_and_keyword_results(self):
        """Hybrid search should merge semantic and keyword results."""
        sem_result = make_result(chunk_id="chunk-sem", score=0.9)
        kw_result = make_result(chunk_id="chunk-kw", note_id="note-002", score=0.8)

        sem_service = MagicMock()
        sem_service.search.return_value = [sem_result]
        kw_service = MagicMock()
        kw_service.search.return_value = [kw_result]
        meta_service = MetadataSearchService()

        service = HybridSearchService(
            semantic_service=sem_service,
            keyword_service=kw_service,
            metadata_service=meta_service,
        )

        query = SearchQuery(query="pump vibration", top_k=10)
        with patch("ertmac.rag.services.hybrid_search_service.global_provenance_adapter") as prov:
            prov.build_provenance.return_value = ProvenanceInfo(note_id="note-001")
            results = service.search(query=query)

        chunk_ids = {r.chunk_id for r in results}
        assert "chunk-sem" in chunk_ids
        assert "chunk-kw" in chunk_ids

    def test_deduplication_keeps_highest_score(self):
        """Duplicate chunk_ids should be deduplicated, keeping the highest score."""
        result_sem = make_result(chunk_id="chunk-dup", score=0.9)
        result_sem.semantic_score = 0.9
        result_kw = make_result(chunk_id="chunk-dup", score=0.7)
        result_kw.keyword_score = 0.7

        sem_service = MagicMock()
        sem_service.search.return_value = [result_sem]
        kw_service = MagicMock()
        kw_service.search.return_value = [result_kw]

        service = HybridSearchService(
            semantic_service=sem_service,
            keyword_service=kw_service,
        )

        query = SearchQuery(query="test", top_k=10)
        with patch("ertmac.rag.services.hybrid_search_service.global_provenance_adapter") as prov:
            prov.build_provenance.return_value = ProvenanceInfo(note_id="note-001")
            results = service.search(query=query)

        dup_results = [r for r in results if r.chunk_id == "chunk-dup"]
        assert len(dup_results) == 1

    def test_empty_query_returns_empty(self):
        """Empty query string should return empty list."""
        service = HybridSearchService()
        results = service.search(query=SearchQuery(query=""))
        assert results == []

    def test_results_sorted_by_score_descending(self):
        """Results must be ordered from highest to lowest score."""
        results_sem = [
            make_result(chunk_id=f"chunk-{i}", score=float(i) / 10)
            for i in range(1, 5)
        ]
        sem_service = MagicMock()
        sem_service.search.return_value = results_sem
        kw_service = MagicMock()
        kw_service.search.return_value = []

        service = HybridSearchService(
            semantic_service=sem_service,
            keyword_service=kw_service,
        )
        query = SearchQuery(query="test")
        with patch("ertmac.rag.services.hybrid_search_service.global_provenance_adapter") as prov:
            prov.build_provenance.return_value = ProvenanceInfo(note_id="note-001")
            results = service.search(query=query)

        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)
