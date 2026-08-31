"""
RAG API Pydantic Schemas
=========================
Request and response models for all RAG endpoints.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ── Request Schemas ────────────────────────────────────────────────────────

class IndexNoteRequest(BaseModel):
    note_id: str = Field(..., description="UUID of the verified handwritten note to index")
    force_reindex: bool = Field(
        default=False,
        description="If true, deletes existing index and rebuilds. Use for corrections."
    )


class SearchFiltersSchema(BaseModel):
    date_from: Optional[str] = Field(None, description="ISO date string e.g. '2026-08-01'")
    date_to: Optional[str] = Field(None, description="ISO date string e.g. '2026-08-31'")
    tags: Optional[List[str]] = Field(None, description="Tag filters e.g. ['Maintenance', 'Vibration']")
    document_type: Optional[str] = Field(None, description="Document type label filter")
    identifiers: Optional[List[str]] = Field(
        None, description="Exact identifier matches e.g. ['MUD-PUMP-008']"
    )
    numeric_filters: Optional[Dict[str, float]] = Field(
        None, description="Numeric field filters e.g. {'pressure_min': 100}"
    )
    organization_id: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query text")
    top_k: int = Field(default=10, ge=1, le=50, description="Maximum results to return")
    mode: str = Field(
        default="hybrid",
        description="Search mode: hybrid | semantic | keyword | metadata"
    )
    filters: Optional[SearchFiltersSchema] = None
    semantic_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.4, ge=0.0, le=1.0)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question")
    top_k: int = Field(default=10, ge=1, le=50)
    filters: Optional[SearchFiltersSchema] = None


# ── Response Schemas ───────────────────────────────────────────────────────

class ProvenanceSchema(BaseModel):
    note_id: str
    chunk_id: Optional[str] = None
    source_file_id: Optional[str] = None
    ocr_run_id: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    version: int = 1
    verification_status: str = "VERIFIED"


class SearchResultSchema(BaseModel):
    note_id: str
    chunk_id: str
    title: str
    section: str
    text: str
    score: float
    metadata: Dict[str, Any] = {}
    provenance: Optional[ProvenanceSchema] = None
    score_breakdown: Optional[Dict[str, Optional[float]]] = None


class SearchResponse(BaseModel):
    success: bool
    query: str
    mode: str
    results: List[SearchResultSchema]
    result_count: int
    duration_ms: Optional[float] = None


class SourceCitationSchema(BaseModel):
    citation_index: int
    note_id: str
    chunk_id: str
    title: str
    section: str
    relevance_score: float
    verified_at: Optional[str] = None
    verified_by: Optional[str] = None
    source_file_id: Optional[str] = None
    ocr_run_id: Optional[str] = None
    text_preview: Optional[str] = None


class QueryResponse(BaseModel):
    success: bool
    question: str
    answer: str
    sources: List[SourceCitationSchema]
    llm_used: bool
    retrieval_count: int
    insufficient_information: bool
    context_truncated: bool = False
    duration_ms: Optional[float] = None


class IndexResponse(BaseModel):
    success: bool
    status: str
    note_id: str
    rag_document_id: Optional[str] = None
    chunk_count: int = 0
    version: int = 1
    skipped: bool = False
    error: Optional[str] = None
    duration_ms: Optional[float] = None


class RAGDocumentInfoResponse(BaseModel):
    note_id: str
    status: str
    chunk_count: int
    version: int
    indexed_at: Optional[str] = None
    content_hash_prefix: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    source_file_id: Optional[str] = None
    ocr_run_id: Optional[str] = None


class RAGHealthResponse(BaseModel):
    status: str
    rag_enabled: bool
    embedding_provider: str
    vector_store: str
    llm_enabled: bool
    llm_provider: Optional[str] = None
    embedding_healthy: bool
    vector_store_healthy: bool
    details: Dict[str, Any] = {}
