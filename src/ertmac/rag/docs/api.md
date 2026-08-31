# RAG Module — API Reference

Base URL: `/api/v1/rag`

All endpoints require authentication via the existing JWT Bearer token.

---

## POST /api/v1/rag/index

Index a verified handwritten note into the RAG system.

**Auth:** `VERIFY_NOTES` permission required

**Request Body:**
```json
{
    "note_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "force_reindex": false
}
```

**Response 200:**
```json
{
    "success": true,
    "status": "INDEXED",
    "note_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "rag_document_id": "8c9b3a12-...",
    "chunk_count": 7,
    "version": 1,
    "skipped": false,
    "error": null,
    "duration_ms": 234.5
}
```

**Rejection cases:**
- `verification_status != VERIFIED` → `status: "REJECTED"`
- `verified_text` is empty → `status: "REJECTED"`
- Note not found → `status: "REJECTED"`

---

## POST /api/v1/rag/search

Hybrid search over indexed verified documents.

**Auth:** `VIEW_HISTORICAL_DATA` permission required

**Request Body:**
```json
{
    "query": "high vibration detected near pump",
    "top_k": 10,
    "mode": "hybrid",
    "filters": {
        "date_from": "2026-08-01",
        "date_to": "2026-08-31",
        "tags": ["Maintenance", "Vibration"],
        "identifiers": ["MUD-PUMP-008"]
    },
    "semantic_weight": 0.6,
    "keyword_weight": 0.4
}
```

**Search Modes:**
| Mode | Description |
|---|---|
| `hybrid` | Semantic + keyword + metadata (default) |
| `semantic` | Vector similarity only |
| `keyword` | Full-text/exact match only |
| `metadata` | Filter-only |

**Response 200:**
```json
{
    "success": true,
    "query": "high vibration detected near pump",
    "mode": "hybrid",
    "result_count": 3,
    "duration_ms": 89.2,
    "results": [
        {
            "note_id": "3fa85f64-...",
            "chunk_id": "a1b2c3d4-...",
            "title": "Daily Drilling Report — 31 Aug 2026",
            "section": "observations",
            "text": "High vibration detected near mud pump at 0600 HRS...",
            "score": 0.923,
            "metadata": {
                "tags": ["Maintenance"],
                "date": "2026-08-31"
            },
            "provenance": {
                "note_id": "3fa85f64-...",
                "chunk_id": "a1b2c3d4-...",
                "source_file_id": "file-001",
                "ocr_run_id": "run-abc",
                "verified_by": "engineer-001",
                "verified_at": "2026-08-31T10:00:00Z",
                "version": 1,
                "verification_status": "VERIFIED"
            },
            "score_breakdown": {
                "semantic": 0.912,
                "keyword": 0.743,
                "metadata": null
            }
        }
    ]
}
```

---

## POST /api/v1/rag/query

Ask a natural language question using retrieved verified documents (RAG Q&A).

**Auth:** `VIEW_HISTORICAL_DATA` permission required

**Request Body:**
```json
{
    "question": "What vibration issues were reported in August 2026?",
    "top_k": 10,
    "filters": {
        "date_from": "2026-08-01",
        "date_to": "2026-08-31"
    }
}
```

**Response 200 (LLM disabled — search-only mode):**
```json
{
    "success": true,
    "question": "What vibration issues were reported in August 2026?",
    "answer": "Found 3 relevant verified document sections...\n1. [Daily Report — observations] ...",
    "llm_used": false,
    "retrieval_count": 3,
    "insufficient_information": false,
    "context_truncated": false,
    "duration_ms": 95.1,
    "sources": [
        {
            "citation_index": 1,
            "note_id": "3fa85f64-...",
            "chunk_id": "a1b2c3d4-...",
            "title": "Daily Drilling Report",
            "section": "observations",
            "relevance_score": 0.923,
            "verified_at": "2026-08-31T10:00:00Z",
            "verified_by": "engineer-001",
            "source_file_id": "file-001",
            "text_preview": "High vibration detected near mud pump..."
        }
    ]
}
```

**Response when insufficient information:**
```json
{
    "success": true,
    "answer": "I could not find sufficient verified information in the indexed documents...",
    "insufficient_information": true,
    "sources": [],
    "retrieval_count": 0
}
```

---

## GET /api/v1/rag/documents/{note_id}

Get RAG indexing information for a specific note.

**Auth:** `VIEW_HISTORICAL_DATA` permission required

**Response 200:**
```json
{
    "note_id": "3fa85f64-...",
    "status": "INDEXED",
    "chunk_count": 7,
    "version": 2,
    "indexed_at": "2026-08-31T12:00:00Z",
    "content_hash_prefix": "a3f9c21b4d...",
    "verified_by": "engineer-001",
    "verified_at": "2026-08-31T10:00:00Z",
    "source_file_id": "file-001",
    "ocr_run_id": "run-abc"
}
```

**Response 404:** Note has never been indexed.

---

## POST /api/v1/rag/reindex/{note_id}

Force-reindex a verified note (deletes existing chunks, rebuilds).

**Auth:** `VERIFY_NOTES` permission required

Same response shape as `POST /api/v1/rag/index`.

---

## DELETE /api/v1/rag/index/{note_id}

Remove a note from the RAG index only.

> **This does NOT delete the source handwritten note, original image, or OCR data.**

**Auth:** `VERIFY_NOTES` permission required

**Response 200:**
```json
{
    "success": true,
    "note_id": "3fa85f64-...",
    "chunks_deleted": 7
}
```

---

## GET /api/v1/rag/health

RAG subsystem health check.

**Auth:** Any authenticated user

**Response 200:**
```json
{
    "status": "HEALTHY",
    "rag_enabled": true,
    "embedding_provider": "sentence_transformers",
    "vector_store": "pgvector",
    "llm_enabled": false,
    "llm_provider": null,
    "embedding_healthy": true,
    "vector_store_healthy": true,
    "details": {
        "embedding_model": "all-MiniLM-L6-v2",
        "llm_model": null,
        "chunk_size": "512",
        "top_k": "10"
    }
}
```

**Status values:**
- `HEALTHY` — All subsystems operational
- `DEGRADED` — One or more subsystems unavailable (search may still work partially)
