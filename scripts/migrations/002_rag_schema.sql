-- ============================================================
-- PS121 RAG SYSTEM — MIGRATION 002
-- Adds: vector extension, rag_documents, rag_chunks, GIN & HNSW indexes
-- Compatible with: Supabase PostgreSQL
-- ============================================================

-- 1. Enable pgvector extension (pre-installed in Supabase)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create rag_documents table (document index & provenance tracking)
CREATE TABLE IF NOT EXISTS rag_documents (
    id              TEXT PRIMARY KEY,
    note_id         TEXT NOT NULL,
    source_version  INTEGER NOT NULL DEFAULT 1,
    content_hash    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'INDEXED'
                        CHECK (status IN ('PENDING', 'INDEXED', 'FAILED', 'REMOVED')),
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    indexed_at      TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    error_message   TEXT,
    ocr_run_id      TEXT,
    source_file_id  TEXT,
    verified_by     TEXT,
    verified_at     TIMESTAMPTZ,
    organization_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_rag_documents_note_id ON rag_documents(note_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_status ON rag_documents(status);
CREATE INDEX IF NOT EXISTS idx_rag_documents_content_hash ON rag_documents(content_hash);

-- 3. Create rag_chunks table (dense embeddings + metadata + full text)
CREATE TABLE IF NOT EXISTS rag_chunks (
    id              TEXT PRIMARY KEY,
    rag_document_id TEXT NOT NULL,
    note_id         TEXT NOT NULL,
    chunk_index     INTEGER NOT NULL DEFAULT 0,
    section         TEXT NOT NULL DEFAULT 'body',
    content         TEXT NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{}',
    embedding       vector(384),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Search Indexes
CREATE INDEX IF NOT EXISTS idx_rag_chunks_note_id ON rag_chunks(note_id);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_rag_document_id ON rag_chunks(rag_document_id);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_section ON rag_chunks(section);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_metadata ON rag_chunks USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_content_fts ON rag_chunks USING GIN(to_tsvector('english', content));

-- Vector similarity index (HNSW for production cosine search)
CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding_hnsw 
    ON rag_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
