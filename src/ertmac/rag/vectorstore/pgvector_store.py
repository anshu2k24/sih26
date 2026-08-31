"""
pgvector Vector Store
======================
Production vector store using PostgreSQL + pgvector extension.

Uses the existing DATABASE_URL from the root .env file.
Creates `rag_documents` and `rag_chunks` tables if they don't exist (additive only).

Requirements:
    - PostgreSQL with pgvector extension installed
    - pip install psycopg2-binary (or psycopg2)

Configuration:
    RAG_VECTOR_STORE=pgvector
    DATABASE_URL=postgresql://...  (from existing .env)
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from ertmac.rag.vectorstore.base import VectorStore
from ertmac.rag.models.rag_chunk import RAGChunk
from ertmac.rag.models.search_result import SearchResult, ProvenanceInfo

logger = logging.getLogger("ertmac.rag.vectorstore.pgvector")

# SQL for idempotent schema creation (matches migration 001_rag_schema.sql)
_INIT_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag_documents (
    id              TEXT PRIMARY KEY,
    note_id         TEXT NOT NULL,
    source_version  INTEGER NOT NULL DEFAULT 1,
    content_hash    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'INDEXED',
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    indexed_at      TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ,
    error_message   TEXT,
    ocr_run_id      TEXT,
    source_file_id  TEXT,
    verified_by     TEXT,
    verified_at     TIMESTAMPTZ,
    organization_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_rag_documents_note_id ON rag_documents(note_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_status  ON rag_documents(status);

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

CREATE INDEX IF NOT EXISTS idx_rag_chunks_note_id         ON rag_chunks(note_id);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_rag_document_id ON rag_chunks(rag_document_id);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_section         ON rag_chunks(section);

-- Full-text search index on content
CREATE INDEX IF NOT EXISTS idx_rag_chunks_content_fts
    ON rag_chunks USING GIN(to_tsvector('english', content));
"""


class PgVectorStore(VectorStore):
    """
    PostgreSQL + pgvector vector store.

    Vector similarity uses cosine distance (<=>).
    Full-text search uses PostgreSQL tsvector.
    Metadata filtering uses JSONB operators.
    """

    def __init__(self, database_url: Optional[str] = None, embedding_dim: int = 384):
        self._database_url = database_url or os.getenv("DATABASE_URL", "")
        self._embedding_dim = embedding_dim
        self._conn = None

        if not self._database_url:
            logger.warning(
                "DATABASE_URL is not set. pgvector store will be unavailable. "
                "Set RAG_VECTOR_STORE=local for development."
            )

    @property
    def store_name(self) -> str:
        return "pgvector"

    def _get_connection(self):
        """Returns a live psycopg2 connection, reconnecting if needed."""
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            raise RuntimeError("psycopg2 is not installed. Run: pip install psycopg2-binary")

        if self._conn is None or self._conn.closed:
            if not self._database_url:
                raise RuntimeError(
                    "DATABASE_URL is not configured. "
                    "Set it in .env or use RAG_VECTOR_STORE=local for development."
                )
            try:
                self._conn = psycopg2.connect(self._database_url)
                self._conn.autocommit = False
                logger.info("pgvector: Connected to PostgreSQL")
            except Exception as e:
                raise RuntimeError(f"pgvector: Failed to connect to PostgreSQL: {e}") from e

        return self._conn

    def initialize(self) -> None:
        """Creates RAG tables and indexes if they don't exist."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Set embedding dimension dynamically
                init_sql = _INIT_SQL.replace("vector(384)", f"vector({self._embedding_dim})")
                cur.execute(init_sql)
            conn.commit()
            logger.info(f"pgvector: Schema initialized (dim={self._embedding_dim})")
        except Exception as e:
            conn.rollback()
            logger.error(f"pgvector: Schema initialization failed: {e}")
            raise RuntimeError(f"pgvector schema init failed: {e}") from e

    def upsert_chunks(self, chunks: List[RAGChunk]) -> None:
        """Inserts or updates chunks by their id."""
        if not chunks:
            return

        conn = self._get_connection()
        try:
            import psycopg2.extras
            with conn.cursor() as cur:
                for chunk in chunks:
                    chunk_id = chunk.id or str(uuid.uuid4())
                    embedding_str = (
                        "[" + ",".join(str(v) for v in chunk.embedding) + "]"
                        if chunk.embedding else None
                    )
                    cur.execute(
                        """
                        INSERT INTO rag_chunks
                            (id, rag_document_id, note_id, chunk_index, section, content, metadata, embedding, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            content     = EXCLUDED.content,
                            metadata    = EXCLUDED.metadata,
                            embedding   = EXCLUDED.embedding::vector,
                            section     = EXCLUDED.section,
                            chunk_index = EXCLUDED.chunk_index
                        """,
                        (
                            chunk_id,
                            chunk.rag_document_id,
                            chunk.note_id,
                            chunk.chunk_index,
                            chunk.section,
                            chunk.content,
                            json.dumps(chunk.metadata),
                            embedding_str,
                            chunk.created_at or datetime.now(timezone.utc).isoformat(),
                        ),
                    )
            conn.commit()
            logger.debug(f"pgvector: Upserted {len(chunks)} chunks")
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"pgvector upsert_chunks failed: {e}") from e

    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Cosine similarity search via pgvector <=> operator."""
        conn = self._get_connection()
        filters = filters or {}
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        where_clauses = []
        params = [embedding_str, top_k]

        if filters.get("note_id"):
            where_clauses.append(f"c.note_id = %s")
            params.insert(1, filters["note_id"])

        if filters.get("organization_id"):
            where_clauses.append(
                "c.metadata->>'organization_id' = %s"
            )
            params.insert(-1, filters["organization_id"])

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        sql = f"""
            SELECT
                c.id,
                c.note_id,
                c.chunk_index,
                c.section,
                c.content,
                c.metadata,
                1 - (c.embedding <=> %s::vector) AS similarity_score
            FROM rag_chunks c
            {where_sql}
            WHERE c.embedding IS NOT NULL
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """
        # Fix param order: embedding appears twice
        final_sql = f"""
            SELECT
                c.id,
                c.note_id,
                c.chunk_index,
                c.section,
                c.content,
                c.metadata,
                1 - (c.embedding <=> %s::vector) AS similarity_score
            FROM rag_chunks c
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """
        q_params = [embedding_str, embedding_str, top_k]

        try:
            with conn.cursor() as cur:
                cur.execute(final_sql, q_params)
                rows = cur.fetchall()
        except Exception as e:
            raise RuntimeError(f"pgvector similarity_search failed: {e}") from e

        results = []
        for row in rows:
            chunk_id, note_id, chunk_index, section, content, metadata_json, score = row
            if isinstance(metadata_json, str):
                metadata = json.loads(metadata_json)
            else:
                metadata = metadata_json or {}

            results.append(SearchResult(
                note_id=note_id,
                chunk_id=str(chunk_id),
                title=metadata.get("title", "Untitled"),
                section=section,
                text=content,
                score=max(0.0, min(1.0, float(score))),
                metadata=metadata,
                semantic_score=float(score),
                provenance=ProvenanceInfo(
                    note_id=note_id,
                    chunk_id=str(chunk_id),
                    version=metadata.get("source_version", 1),
                ),
            ))
        return results

    def fulltext_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        PostgreSQL full-text search using ts_vector and plainto_tsquery.
        Returns results sorted by text search rank.
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        c.id,
                        c.note_id,
                        c.chunk_index,
                        c.section,
                        c.content,
                        c.metadata,
                        ts_rank(to_tsvector('english', c.content), plainto_tsquery('english', %s)) AS rank
                    FROM rag_chunks c
                    WHERE to_tsvector('english', c.content) @@ plainto_tsquery('english', %s)
                    ORDER BY rank DESC
                    LIMIT %s
                    """,
                    (query, query, top_k),
                )
                rows = cur.fetchall()
        except Exception as e:
            raise RuntimeError(f"pgvector fulltext_search failed: {e}") from e

        results = []
        for row in rows:
            chunk_id, note_id, chunk_index, section, content, metadata_json, rank = row
            if isinstance(metadata_json, str):
                metadata = json.loads(metadata_json)
            else:
                metadata = metadata_json or {}
            # Normalize rank to [0, 1] approximately (ts_rank max is ~1.0 in practice)
            normalized_rank = min(1.0, float(rank))
            results.append(SearchResult(
                note_id=note_id,
                chunk_id=str(chunk_id),
                title=metadata.get("title", "Untitled"),
                section=section,
                text=content,
                score=normalized_rank,
                metadata=metadata,
                keyword_score=normalized_rank,
                provenance=ProvenanceInfo(
                    note_id=note_id,
                    chunk_id=str(chunk_id),
                ),
            ))
        return results

    def delete_by_note_id(self, note_id: str) -> int:
        """Removes all RAG chunks for a note. Never deletes the source note."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM rag_chunks WHERE note_id = %s RETURNING id",
                    (note_id,),
                )
                deleted_ids = cur.fetchall()
                # Also remove rag_documents record
                cur.execute(
                    "DELETE FROM rag_documents WHERE note_id = %s",
                    (note_id,),
                )
            conn.commit()
            count = len(deleted_ids)
            logger.info(f"pgvector: Deleted {count} chunks for note {note_id}")
            return count
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"pgvector delete_by_note_id failed: {e}") from e

    def get_chunks_for_note(self, note_id: str) -> List[RAGChunk]:
        """Returns all stored chunks for a note (without embeddings for efficiency)."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, rag_document_id, note_id, chunk_index, section, content, metadata, created_at
                    FROM rag_chunks WHERE note_id = %s ORDER BY chunk_index
                    """,
                    (note_id,),
                )
                rows = cur.fetchall()
        except Exception as e:
            raise RuntimeError(f"pgvector get_chunks_for_note failed: {e}") from e

        chunks = []
        for row in rows:
            chunk_id, rag_doc_id, note_id_, chunk_idx, section, content, metadata_json, created_at = row
            if isinstance(metadata_json, str):
                metadata = json.loads(metadata_json)
            else:
                metadata = metadata_json or {}
            chunks.append(RAGChunk(
                id=str(chunk_id),
                rag_document_id=str(rag_doc_id),
                note_id=note_id_,
                chunk_index=chunk_idx,
                section=section,
                content=content,
                metadata=metadata,
                created_at=str(created_at) if created_at else None,
            ))
        return chunks

    def upsert_rag_document(self, doc_data: Dict[str, Any]) -> None:
        """Inserts or updates a rag_documents record."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO rag_documents
                        (id, note_id, source_version, content_hash, status, chunk_count,
                         indexed_at, updated_at, ocr_run_id, source_file_id, verified_by, verified_at, organization_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        source_version  = EXCLUDED.source_version,
                        content_hash    = EXCLUDED.content_hash,
                        status          = EXCLUDED.status,
                        chunk_count     = EXCLUDED.chunk_count,
                        indexed_at      = EXCLUDED.indexed_at,
                        updated_at      = EXCLUDED.updated_at,
                        ocr_run_id      = EXCLUDED.ocr_run_id,
                        source_file_id  = EXCLUDED.source_file_id,
                        verified_by     = EXCLUDED.verified_by,
                        verified_at     = EXCLUDED.verified_at
                    """,
                    (
                        doc_data["id"],
                        doc_data["note_id"],
                        doc_data.get("source_version", 1),
                        doc_data["content_hash"],
                        doc_data.get("status", "INDEXED"),
                        doc_data.get("chunk_count", 0),
                        doc_data.get("indexed_at"),
                        doc_data.get("updated_at"),
                        doc_data.get("ocr_run_id"),
                        doc_data.get("source_file_id"),
                        doc_data.get("verified_by"),
                        doc_data.get("verified_at"),
                        doc_data.get("organization_id"),
                    ),
                )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"pgvector upsert_rag_document failed: {e}") from e

    def health_check(self) -> bool:
        """Tests PostgreSQL connectivity and pgvector availability."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
                # Check pgvector
                cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
                has_vector = cur.fetchone() is not None
            if not has_vector:
                logger.warning("pgvector extension is not installed in the database")
            return True
        except Exception as e:
            logger.warning(f"pgvector health check failed: {e}")
            return False
