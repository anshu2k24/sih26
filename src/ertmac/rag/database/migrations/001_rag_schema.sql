-- ============================================================
-- SIH 2026 PS121 — RAG Module — Additive Database Migration
-- Migration: 001_rag_schema.sql
-- 
-- ADDITIVE ONLY — this migration:
--   ✓ Creates new tables: rag_documents, rag_chunks
--   ✓ Creates new indexes
--   ✓ Enables pgvector extension
--
--   ✗ Does NOT drop existing tables
--   ✗ Does NOT modify: handwritten_notes, ocr_runs, ocr_audit_logs, profiles
--   ✗ Does NOT rename or alter existing columns
--
-- Apply with: python src/ertmac/rag/database/migrate.py
-- ============================================================

-- Step 1: Enable pgvector extension
-- (requires PostgreSQL with pgvector installed, or Supabase which includes it)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- TABLE: rag_documents
-- Tracks which handwritten notes have been indexed into RAG.
-- References handwritten_notes by note_id (no FK to avoid coupling).
-- ============================================================
CREATE TABLE IF NOT EXISTS rag_documents (
    id              TEXT PRIMARY KEY,
    note_id         TEXT NOT NULL,           -- References handwritten_notes.id (soft ref)
    source_version  INTEGER NOT NULL DEFAULT 1,
    content_hash    TEXT NOT NULL,           -- SHA-256 of verified_text at index time
    status          TEXT NOT NULL DEFAULT 'INDEXED'
                        CHECK (status IN ('PENDING', 'INDEXED', 'FAILED', 'REMOVED')),
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    indexed_at      TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    error_message   TEXT,

    -- Provenance references (copied at index time, never re-derived)
    ocr_run_id      TEXT,                    -- References ocr_runs.id (soft ref)
    source_file_id  TEXT,                    -- References stored image file
    verified_by     TEXT,                    -- User who verified the note
    verified_at     TIMESTAMPTZ,

    -- Access control preparation (future multi-tenant)
    organization_id TEXT
);

-- Indexes for rag_documents
CREATE INDEX IF NOT EXISTS idx_rag_documents_note_id        ON rag_documents(note_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_status         ON rag_documents(status);
CREATE INDEX IF NOT EXISTS idx_rag_documents_organization   ON rag_documents(organization_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_content_hash   ON rag_documents(content_hash);


-- ============================================================
-- TABLE: rag_chunks
-- Stores searchable text chunks with vector embeddings.
-- Each chunk maps back to exactly one rag_document and note.
-- ============================================================
CREATE TABLE IF NOT EXISTS rag_chunks (
    id              TEXT PRIMARY KEY,
    rag_document_id TEXT NOT NULL,           -- References rag_documents.id
    note_id         TEXT NOT NULL,           -- References handwritten_notes.id (soft ref)
    chunk_index     INTEGER NOT NULL DEFAULT 0,
    section         TEXT NOT NULL DEFAULT 'body',
    content         TEXT NOT NULL,

    -- Metadata JSONB for flexible structured filtering
    -- Contains: title, dates, tags, identifiers, measurements, organization_id, source_version
    metadata        JSONB NOT NULL DEFAULT '{}',

    -- Vector embedding column (384 dimensions for all-MiniLM-L6-v2)
    -- Adjust dimension if using a different embedding model
    embedding       vector(384),

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for rag_chunks — covering the most important retrieval patterns
CREATE INDEX IF NOT EXISTS idx_rag_chunks_note_id
    ON rag_chunks(note_id);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_rag_document_id
    ON rag_chunks(rag_document_id);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_section
    ON rag_chunks(section);

-- Full-text search index (PostgreSQL GIN)
CREATE INDEX IF NOT EXISTS idx_rag_chunks_content_fts
    ON rag_chunks USING GIN(to_tsvector('english', content));

-- JSONB index for metadata filtering (tags, dates, identifiers)
CREATE INDEX IF NOT EXISTS idx_rag_chunks_metadata
    ON rag_chunks USING GIN(metadata);

-- ============================================================
-- OPTIONAL: HNSW vector index for production performance
-- (requires pgvector >= 0.5.0)
-- Uncomment for large-scale deployments (>100k chunks):
-- ============================================================
-- CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding_hnsw
--     ON rag_chunks USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);

-- For smaller datasets, IVFFlat is sufficient:
-- CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding_ivfflat
--     ON rag_chunks USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);
