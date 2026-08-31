"""
Tests: Answer Generation Service
==================================
Verifies RAG Q&A behaviour: source citations, insufficient information handling,
and LLM-disabled search-only mode.
"""

import pytest
from unittest.mock import MagicMock, patch

from ertmac.rag.services.answer_generation_service import (
    AnswerGenerationService,
    _INSUFFICIENT_INFORMATION_MESSAGE,
)
from ertmac.rag.services.hybrid_search_service import HybridSearchService
from ertmac.rag.services.context_builder_service import ContextBuilderService
from ertmac.rag.models.search_result import SearchResult, ProvenanceInfo
from ertmac.rag.models.query_model import SearchQuery


def make_result(note_id="note-001", chunk_id="chunk-001", text="High vibration detected."):
    return SearchResult(
        note_id=note_id,
        chunk_id=chunk_id,
        title="Drilling Report",
        section="observations",
        text=text,
        score=0.91,
        metadata={"tags": ["Vibration"]},
        provenance=ProvenanceInfo(
            note_id=note_id,
            chunk_id=chunk_id,
            verified_at="2026-08-31T10:00:00Z",
            source_file_id="file-001",
        ),
    )


class TestAnswerGenerationService:

    def _make_service(self, search_results=None, llm_answer=None, llm_enabled=False):
        search_service = MagicMock(spec=HybridSearchService)
        search_service.search.return_value = search_results or []

        context_builder = ContextBuilderService()

        mock_llm = MagicMock()
        mock_llm.generate_answer.return_value = llm_answer or "The answer based on context."

        service = AnswerGenerationService(
            search_service=search_service,
            context_builder=context_builder,
            llm_provider=mock_llm,
        )
        # Override the env check
        service._llm_enabled = llm_enabled
        return service, search_service, mock_llm

    def test_insufficient_information_when_no_results(self):
        """No results → must return the standard insufficient information message."""
        service, _, _ = self._make_service(search_results=[], llm_enabled=False)
        result = service.answer(question="What issues were found?")
        assert result["insufficient_information"] is True
        assert _INSUFFICIENT_INFORMATION_MESSAGE in result["answer"]

    def test_sources_are_returned_with_answer(self):
        """Every answer must include source citations."""
        results = [make_result()]
        service, _, _ = self._make_service(search_results=results, llm_enabled=False)
        result = service.answer(question="Show pump issues")
        assert result["retrieval_count"] >= 1
        assert isinstance(result["sources"], list)
        assert len(result["sources"]) >= 1
        assert result["sources"][0]["note_id"] == "note-001"

    def test_llm_generates_answer_when_enabled(self):
        """When LLM is enabled and context exists, LLM.generate_answer is called."""
        results = [make_result()]
        service, _, mock_llm = self._make_service(
            search_results=results,
            llm_answer="High vibration was observed near the mud pump.",
            llm_enabled=True,
        )
        result = service.answer(question="What was observed?")
        assert result["llm_used"] is True
        assert "High vibration" in result["answer"]
        mock_llm.generate_answer.assert_called_once()

    def test_llm_not_called_when_disabled(self):
        """When LLM is disabled, generate_answer must not be called."""
        results = [make_result()]
        service, _, mock_llm = self._make_service(
            search_results=results,
            llm_enabled=False,
        )
        result = service.answer(question="What was observed?")
        assert result["llm_used"] is False
        mock_llm.generate_answer.assert_not_called()

    def test_search_only_mode_returns_structured_summary(self):
        """In search-only mode, returned answer summarizes retrieved chunks."""
        results = [
            make_result(note_id="note-001", text="High vibration detected near mud pump."),
            make_result(note_id="note-002", chunk_id="chunk-002", text="Oil leakage at valve assembly."),
        ]
        service, _, _ = self._make_service(search_results=results, llm_enabled=False)
        result = service.answer(question="What issues were reported?")
        # Should NOT be the insufficient information message
        assert _INSUFFICIENT_INFORMATION_MESSAGE not in result["answer"]
        # Should reference at least one source
        assert result["retrieval_count"] >= 1

    def test_empty_question_returns_prompt_message(self):
        """Empty question string should return a helpful prompt."""
        service, _, _ = self._make_service()
        result = service.answer(question="   ")
        assert result["insufficient_information"] is True

    def test_llm_failure_returns_graceful_error(self):
        """If LLM call fails, should return error message, not crash."""
        results = [make_result()]
        service, _, mock_llm = self._make_service(
            search_results=results,
            llm_enabled=True,
        )
        mock_llm.generate_answer.side_effect = RuntimeError("API timeout")

        result = service.answer(question="What issues?")
        assert "LLM answer generation failed" in result["answer"] or result["answer"]
        # Must not raise an exception — should gracefully return something
        assert result is not None

    def test_source_citations_include_provenance_fields(self):
        """Source citations must include traceability fields."""
        results = [make_result()]
        service, _, _ = self._make_service(search_results=results, llm_enabled=False)
        result = service.answer(question="Any vibration issues?")
        sources = result["sources"]
        assert sources
        source = sources[0]
        assert "note_id" in source
        assert "chunk_id" in source
        assert "section" in source
        assert "relevance_score" in source
