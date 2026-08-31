/**
 * RAG Intelligent Search API Service
 * ====================================
 * TypeScript client for all RAG API endpoints.
 *
 * ADDITIVE ONLY — does not modify existing notesApi.ts or api.ts.
 *
 * Base URL: /api/v1/rag
 */

const RAG_BASE_URL = "/api/v1/rag";

// ── Helper ───────────────────────────────────────────────────────────────

async function ragFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${RAG_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `RAG API error: ${res.status}`);
  }
  return res.json();
}

// ── Types ─────────────────────────────────────────────────────────────────

export interface SearchFilters {
  date_from?: string;
  date_to?: string;
  tags?: string[];
  document_type?: string;
  identifiers?: string[];
  organization_id?: string;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  mode?: "hybrid" | "semantic" | "keyword" | "metadata";
  filters?: SearchFilters;
  semantic_weight?: number;
  keyword_weight?: number;
}

export interface QueryRequest {
  question: string;
  top_k?: number;
  filters?: SearchFilters;
}

export interface IndexRequest {
  note_id: string;
  force_reindex?: boolean;
}

export interface ProvenanceInfo {
  note_id: string;
  chunk_id: string | null;
  source_file_id: string | null;
  ocr_run_id: string | null;
  verified_by: string | null;
  verified_at: string | null;
  version: number;
  verification_status: string;
}

export interface ScoreBreakdown {
  semantic: number | null;
  keyword: number | null;
  metadata: number | null;
}

export interface SearchResult {
  note_id: string;
  chunk_id: string;
  title: string;
  section: string;
  text: string;
  score: number;
  metadata: Record<string, unknown>;
  provenance: ProvenanceInfo | null;
  score_breakdown: ScoreBreakdown | null;
}

export interface SearchResponse {
  success: boolean;
  query: string;
  mode: string;
  results: SearchResult[];
  result_count: number;
  duration_ms: number | null;
}

export interface SourceCitation {
  citation_index: number;
  note_id: string;
  chunk_id: string;
  title: string;
  section: string;
  relevance_score: number;
  verified_at: string | null;
  verified_by: string | null;
  source_file_id: string | null;
  ocr_run_id: string | null;
  text_preview: string | null;
}

export interface QueryResponse {
  success: boolean;
  question: string;
  answer: string;
  sources: SourceCitation[];
  llm_used: boolean;
  retrieval_count: number;
  insufficient_information: boolean;
  context_truncated: boolean;
  duration_ms: number | null;
}

export interface IndexResponse {
  success: boolean;
  status: string;
  note_id: string;
  rag_document_id: string | null;
  chunk_count: number;
  version: number;
  skipped: boolean;
  error: string | null;
  duration_ms: number | null;
}

export interface RAGDocumentInfo {
  note_id: string;
  status: string;
  chunk_count: number;
  version: number;
  indexed_at: string | null;
  content_hash_prefix: string | null;
  verified_by: string | null;
  verified_at: string | null;
  source_file_id: string | null;
  ocr_run_id: string | null;
}

export interface RAGHealth {
  status: "HEALTHY" | "DEGRADED";
  rag_enabled: boolean;
  embedding_provider: string;
  vector_store: string;
  llm_enabled: boolean;
  llm_provider: string | null;
  embedding_healthy: boolean;
  vector_store_healthy: boolean;
  details: Record<string, string | null>;
}

// ── API Functions ─────────────────────────────────────────────────────────

/**
 * Index a verified note into the RAG system.
 */
export async function indexNote(req: IndexRequest): Promise<IndexResponse> {
  return ragFetch<IndexResponse>("/index", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/**
 * Perform hybrid search over indexed verified documents.
 */
export async function ragSearch(req: SearchRequest): Promise<SearchResponse> {
  return ragFetch<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/**
 * Ask a natural language question using retrieved verified documents.
 */
export async function ragQuery(req: QueryRequest): Promise<QueryResponse> {
  return ragFetch<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/**
 * Get RAG indexing metadata for a specific note.
 */
export async function getRAGDocumentInfo(
  noteId: string
): Promise<RAGDocumentInfo> {
  return ragFetch<RAGDocumentInfo>(`/documents/${encodeURIComponent(noteId)}`);
}

/**
 * Force reindex a verified note.
 */
export async function reindexNote(noteId: string): Promise<IndexResponse> {
  return ragFetch<IndexResponse>(`/reindex/${encodeURIComponent(noteId)}`, {
    method: "POST",
  });
}

/**
 * Remove a note from the RAG index (does NOT delete the source note).
 */
export async function removeRAGIndex(
  noteId: string
): Promise<{ success: boolean; note_id: string; chunks_deleted: number }> {
  return ragFetch(`/index/${encodeURIComponent(noteId)}`, {
    method: "DELETE",
  });
}

/**
 * Get RAG subsystem health status.
 */
export async function getRAGHealth(): Promise<RAGHealth> {
  return ragFetch<RAGHealth>("/health");
}
