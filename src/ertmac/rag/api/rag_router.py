"""
RAG API Router
==============
Self-contained FastAPI router for all RAG endpoints.

DO NOT MODIFY existing server.py — this router must be MOUNTED by the integrator.

Integration step (in src/ertmac/api/server.py):
    from ertmac.rag.api.rag_router import router as rag_router
    app.include_router(rag_router)

Routes:
    POST   /api/v1/rag/index                  — Index a verified note
    POST   /api/v1/rag/search                 — Hybrid search
    POST   /api/v1/rag/query                  — RAG Q&A
    GET    /api/v1/rag/documents/{note_id}    — Get indexing info
    POST   /api/v1/rag/reindex/{note_id}      — Force reindex
    DELETE /api/v1/rag/index/{note_id}        — Remove from RAG index only
    GET    /api/v1/rag/health                 — RAG subsystem health
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

# Reuse existing auth — no modifications to auth module
from ertmac.auth.rbac import get_current_user, require_permission, UserSession, Permission

from ertmac.rag.api.rag_schemas import (
    IndexNoteRequest, IndexResponse,
    SearchRequest, SearchResponse,
    QueryRequest, QueryResponse,
    RAGDocumentInfoResponse, RAGHealthResponse,
)
from ertmac.rag.api.rag_controller import (
    handle_index_note,
    handle_search,
    handle_query,
    handle_get_document_info,
    handle_remove_index,
    handle_health_check,
)

logger = logging.getLogger("ertmac.rag.api.router")

router = APIRouter(
    prefix="/api/v1/rag",
    tags=["PS121 RAG Intelligent Search"],
)


@router.post(
    "/index",
    response_model=IndexResponse,
    summary="Index a verified handwritten note into the RAG system",
)
def index_note(
    request: IndexNoteRequest,
    user: UserSession = Depends(require_permission(Permission.VERIFY_NOTES)),
):
    """
    Indexes a verified handwritten note into the RAG search index.

    Requirements:
    - Note must have verification_status == VERIFIED
    - Note must have non-empty verified_text
    - Unverified or failed OCR notes are rejected

    Idempotent: re-indexing the same content version is a no-op.
    Use force_reindex=true to rebuild the index after content corrections.
    """
    try:
        return handle_index_note(request=request, user_id=user.user_id)
    except Exception as e:
        logger.error(f"RAG index error for note {request.note_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG indexing failed: {str(e)}",
        )


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search indexed verified documents using hybrid search",
)
def search_documents(
    request: SearchRequest,
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """
    Performs hybrid search (semantic + keyword + metadata) over indexed verified notes.

    Search modes:
    - hybrid: Combines semantic vector similarity + keyword/full-text (default)
    - semantic: Vector similarity only (e.g., 'machine shaking' → 'high vibration')
    - keyword: Exact/full-text search (e.g., equipment IDs, serial numbers)
    - metadata: Filter-only search (by date, tags, identifiers)

    Example request:
    {
        "query": "pump vibration above threshold",
        "top_k": 10,
        "filters": { "tags": ["Maintenance"], "date_from": "2026-08-01" }
    }
    """
    try:
        return handle_search(request=request, user_id=user.user_id)
    except Exception as e:
        logger.error(f"RAG search error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a question using retrieved verified documents (RAG Q&A)",
)
def query_documents(
    request: QueryRequest,
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """
    Answers a natural language question using retrieved verified documents.

    Pipeline:
    1. Retrieve relevant verified chunks via hybrid search
    2. Build context from retrieved content
    3. Generate answer (requires RAG_LLM_ENABLED=true, otherwise returns search summary)
    4. Return answer + source citations

    CRITICAL: The system never invents information. If sufficient context is not
    found in verified documents, a clear 'insufficient information' message is returned.

    Source citations include note_id, section, verified_at for full traceability.
    """
    try:
        return handle_query(request=request, user_id=user.user_id)
    except Exception as e:
        logger.error(f"RAG query error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}",
        )


@router.get(
    "/documents/{note_id}",
    response_model=RAGDocumentInfoResponse,
    summary="Get RAG indexing information for a note",
)
def get_rag_document_info(
    note_id: str,
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """
    Returns the RAG indexing status, version, and chunk count for a note.
    Useful for checking if a note has been indexed and when.
    """
    info = handle_get_document_info(note_id=note_id)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note '{note_id}' has not been indexed in the RAG system.",
        )
    return info


@router.post(
    "/reindex/{note_id}",
    response_model=IndexResponse,
    summary="Force reindex a verified note (after corrections)",
)
def reindex_note(
    note_id: str,
    user: UserSession = Depends(require_permission(Permission.VERIFY_NOTES)),
):
    """
    Forces a complete reindex of a verified note.
    Deletes existing chunks and regenerates them from the current verified_text.

    Use this after:
    - A human reviewer corrects the verified_text
    - Structured data extraction is updated
    """
    try:
        request = IndexNoteRequest(note_id=note_id, force_reindex=True)
        return handle_index_note(request=request, user_id=user.user_id)
    except Exception as e:
        logger.error(f"RAG reindex error for note {note_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reindex failed: {str(e)}",
        )


@router.delete(
    "/index/{note_id}",
    summary="Remove note from RAG index (does NOT delete source note)",
)
def remove_rag_index(
    note_id: str,
    user: UserSession = Depends(require_permission(Permission.VERIFY_NOTES)),
):
    """
    Removes a note's vector index from the RAG system.

    IMPORTANT: This ONLY removes the RAG index (rag_chunks, rag_documents).
    The source handwritten note in handwritten_notes table is NOT affected.
    The original image and OCR runs are NOT affected.

    Use this when a note needs to be removed from search results.
    """
    try:
        result = handle_remove_index(note_id=note_id, user_id=user.user_id)
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Remove failed"),
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG remove error for note {note_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Remove failed: {str(e)}",
        )


@router.get(
    "/health",
    response_model=RAGHealthResponse,
    summary="RAG subsystem health check",
)
def rag_health_check(
    user: UserSession = Depends(get_current_user),
):
    """
    Returns health status of all RAG subsystems:
    - Embedding provider
    - Vector store
    - LLM (if enabled)

    Status: HEALTHY | DEGRADED
    """
    return handle_health_check()
