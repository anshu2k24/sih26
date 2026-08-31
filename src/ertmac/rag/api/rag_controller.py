"""
RAG Controller
==============
Business logic handlers called by the RAG router.
Keeps the router thin and testable.
"""

import logging
import os
import time
from typing import Optional

from ertmac.rag.api.rag_schemas import (
    IndexNoteRequest, IndexResponse,
    SearchRequest, SearchResponse, SearchResultSchema, ProvenanceSchema,
    QueryRequest, QueryResponse, SourceCitationSchema,
    RAGDocumentInfoResponse, RAGHealthResponse,
)
from ertmac.rag.models.query_model import SearchQuery, SearchFilters, SearchMode
from ertmac.rag.services.ingestion_service import global_ingestion_service
from ertmac.rag.services.hybrid_search_service import global_hybrid_search_service
from ertmac.rag.services.answer_generation_service import global_answer_generation_service
from ertmac.rag.services.embedding_service import global_embedding_service
from ertmac.rag.repositories.document_index_repository import global_document_index_repository
from ertmac.rag.vectorstore.factory import get_vector_store

logger = logging.getLogger("ertmac.rag.api.controller")


def _map_filters(filters_schema) -> SearchFilters:
    """Converts API schema filters to domain SearchFilters."""
    if not filters_schema:
        return SearchFilters()
    return SearchFilters(
        date_from=filters_schema.date_from,
        date_to=filters_schema.date_to,
        tags=filters_schema.tags,
        document_type=filters_schema.document_type,
        identifiers=filters_schema.identifiers,
        numeric_filters=filters_schema.numeric_filters,
        organization_id=filters_schema.organization_id,
    )


def handle_index_note(
    request: IndexNoteRequest,
    user_id: str,
) -> IndexResponse:
    """Indexes a verified note into the RAG system."""
    result = global_ingestion_service.index_note(
        note_id=request.note_id,
        user_id=user_id,
        force_reindex=request.force_reindex,
    )

    return IndexResponse(
        success=result.get("success", False),
        status=result.get("status", "UNKNOWN"),
        note_id=request.note_id,
        rag_document_id=result.get("rag_document_id"),
        chunk_count=result.get("chunk_count", 0),
        version=result.get("version", 1),
        skipped=result.get("skipped", False),
        error=result.get("error"),
        duration_ms=result.get("duration_ms"),
    )


def handle_search(
    request: SearchRequest,
    user_id: Optional[str],
) -> SearchResponse:
    """Executes hybrid search."""
    start = time.time()

    mode_map = {
        "hybrid": SearchMode.HYBRID,
        "semantic": SearchMode.SEMANTIC,
        "keyword": SearchMode.KEYWORD,
        "metadata": SearchMode.METADATA,
    }
    mode = mode_map.get(request.mode.lower(), SearchMode.HYBRID)

    query = SearchQuery(
        query=request.query,
        top_k=request.top_k,
        mode=mode,
        filters=_map_filters(request.filters),
        semantic_weight=request.semantic_weight,
        keyword_weight=request.keyword_weight,
    )

    results = global_hybrid_search_service.search(query=query, user_id=user_id)

    serialized = []
    for r in results:
        prov = None
        if r.provenance:
            prov = ProvenanceSchema(
                note_id=r.provenance.note_id,
                chunk_id=r.provenance.chunk_id,
                source_file_id=r.provenance.source_file_id,
                ocr_run_id=r.provenance.ocr_run_id,
                verified_by=r.provenance.verified_by,
                verified_at=r.provenance.verified_at,
                version=r.provenance.version,
                verification_status=r.provenance.verification_status,
            )
        serialized.append(SearchResultSchema(
            note_id=r.note_id,
            chunk_id=r.chunk_id,
            title=r.title,
            section=r.section,
            text=r.text,
            score=round(r.score, 4),
            metadata=r.metadata,
            provenance=prov,
            score_breakdown=r.to_dict().get("score_breakdown"),
        ))

    return SearchResponse(
        success=True,
        query=request.query,
        mode=request.mode,
        results=serialized,
        result_count=len(serialized),
        duration_ms=round((time.time() - start) * 1000, 1),
    )


def handle_query(
    request: QueryRequest,
    user_id: Optional[str],
) -> QueryResponse:
    """Answers a question using retrieved verified documents."""
    start = time.time()

    search_query = SearchQuery(
        query=request.question,
        top_k=request.top_k,
        filters=_map_filters(request.filters),
    )

    result = global_answer_generation_service.answer(
        question=request.question,
        query=search_query,
        user_id=user_id,
    )

    sources = [
        SourceCitationSchema(
            citation_index=s.get("citation_index", i + 1),
            note_id=s["note_id"],
            chunk_id=s["chunk_id"],
            title=s["title"],
            section=s["section"],
            relevance_score=s["relevance_score"],
            verified_at=s.get("verified_at"),
            verified_by=s.get("verified_by"),
            source_file_id=s.get("source_file_id"),
            ocr_run_id=s.get("ocr_run_id"),
            text_preview=s.get("text_preview"),
        )
        for i, s in enumerate(result.get("sources", []))
    ]

    return QueryResponse(
        success=True,
        question=request.question,
        answer=result["answer"],
        sources=sources,
        llm_used=result.get("llm_used", False),
        retrieval_count=result.get("retrieval_count", 0),
        insufficient_information=result.get("insufficient_information", False),
        context_truncated=result.get("context_truncated", False),
        duration_ms=round((time.time() - start) * 1000, 1),
    )


def handle_get_document_info(note_id: str) -> Optional[RAGDocumentInfoResponse]:
    """Returns indexing metadata for a note."""
    doc = global_document_index_repository.get_by_note_id(note_id)
    if not doc:
        return None
    return RAGDocumentInfoResponse(
        note_id=doc.note_id,
        status=doc.status.value,
        chunk_count=doc.chunk_count,
        version=doc.source_version,
        indexed_at=doc.indexed_at,
        content_hash_prefix=doc.content_hash[:16] + "..." if doc.content_hash else None,
        verified_by=doc.verified_by,
        verified_at=doc.verified_at,
        source_file_id=doc.source_file_id,
        ocr_run_id=doc.ocr_run_id,
    )


def handle_remove_index(note_id: str, user_id: str) -> dict:
    """Removes a note's RAG index. Never deletes the source note."""
    return global_ingestion_service.remove_index(note_id=note_id, user_id=user_id)


def handle_health_check() -> RAGHealthResponse:
    """Returns RAG subsystem health status."""
    rag_enabled = os.getenv("RAG_ENABLED", "true").lower() == "true"
    llm_enabled = os.getenv("RAG_LLM_ENABLED", "false").lower() == "true"

    embedding_healthy = False
    vector_healthy = False

    try:
        embedding_healthy = global_embedding_service.health_check()
    except Exception:
        pass

    try:
        store = get_vector_store()
        vector_healthy = store.health_check()
    except Exception:
        pass

    llm_info = global_answer_generation_service.health_check()

    overall = "HEALTHY" if (embedding_healthy and vector_healthy) else "DEGRADED"

    return RAGHealthResponse(
        status=overall,
        rag_enabled=rag_enabled,
        embedding_provider=os.getenv("RAG_EMBEDDING_PROVIDER", "sentence_transformers"),
        vector_store=os.getenv("RAG_VECTOR_STORE", "local"),
        llm_enabled=llm_enabled,
        llm_provider=llm_info.get("llm_provider") if llm_enabled else None,
        embedding_healthy=embedding_healthy,
        vector_store_healthy=vector_healthy,
        details={
            "embedding_model": os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            "llm_model": llm_info.get("llm_model") if llm_enabled else None,
            "chunk_size": os.getenv("RAG_CHUNK_SIZE", "512"),
            "top_k": os.getenv("RAG_TOP_K", "10"),
        },
    )
