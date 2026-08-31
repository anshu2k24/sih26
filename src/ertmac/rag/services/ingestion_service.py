"""
RAG Ingestion Service
======================
Orchestrates the complete pipeline from a verified note to indexed chunks.

Pipeline:
    note_id
        ↓ Fetch via NotesAdapter (read-only)
        ↓ Validate VERIFIED status
        ↓ Validate non-empty verified_text
        ↓ Compute content_hash (SHA-256)
        ↓ Check duplicate (idempotency)
        ↓ Delete existing chunks (if reindexing)
        ↓ Structure-aware chunking
        ↓ Batch embedding generation
        ↓ Upsert chunks to vector store
        ↓ Update rag_documents record
        ↓ Audit log

Trust boundary: ONLY notes with verification_status == "VERIFIED" are indexed.
"""

import hashlib
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from ertmac.rag.adapters.notes_adapter import global_notes_adapter, NotesAdapter
from ertmac.rag.services.chunking_service import global_chunking_service, ChunkingService
from ertmac.rag.services.embedding_service import global_embedding_service, EmbeddingService
from ertmac.rag.vectorstore.factory import get_vector_store
from ertmac.rag.repositories.document_index_repository import global_document_index_repository, DocumentIndexRepository
from ertmac.rag.repositories.rag_audit_repository import global_rag_audit_repository, RAGAuditEvent
from ertmac.rag.models.rag_document import RAGDocument, RAGDocumentStatus

logger = logging.getLogger("ertmac.rag.services.ingestion")


class IngestionService:
    """
    Handles indexing of verified notes into the RAG system.
    """

    def __init__(
        self,
        notes_adapter: Optional[NotesAdapter] = None,
        chunking_service: Optional[ChunkingService] = None,
        embedding_service: Optional[EmbeddingService] = None,
        doc_index_repo: Optional[DocumentIndexRepository] = None,
    ):
        self._notes = notes_adapter or global_notes_adapter
        self._chunker = chunking_service or global_chunking_service
        self._embedder = embedding_service or global_embedding_service
        self._doc_repo = doc_index_repo or global_document_index_repository

    def index_note(
        self,
        note_id: str,
        user_id: str = "system",
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        """
        Indexes a single verified note into the RAG system.

        Args:
            note_id: The ID of the note to index.
            user_id: The requesting user (for audit).
            force_reindex: If True, delete existing index and rebuild.

        Returns:
            Result dict with status, chunk_count, and any error message.
        """
        start_time = time.time()
        global_rag_audit_repository.log(
            RAGAuditEvent.INDEX_STARTED,
            note_id=note_id,
            user_id=user_id,
        )

        # ── Step 1: Fetch verified note ──────────────────────────────────
        note = self._notes.get_verified_note(note_id)
        if note is None:
            # Check why — note exists but unverified, or doesn't exist?
            note_info = self._notes.get_note_for_ingestion_check(note_id)
            if note_info is None:
                msg = f"Note '{note_id}' not found"
            elif note_info.get("verification_status") != "VERIFIED":
                msg = (
                    f"Note '{note_id}' cannot be indexed — "
                    f"verification_status='{note_info.get('verification_status')}' "
                    f"(must be VERIFIED). Human verification is required."
                )
            elif not note_info.get("has_verified_text"):
                msg = f"Note '{note_id}' has empty verified_text — nothing to index"
            else:
                msg = f"Note '{note_id}' is not eligible for indexing"

            global_rag_audit_repository.log(
                RAGAuditEvent.INDEX_FAILED,
                note_id=note_id,
                user_id=user_id,
                status="failure",
                metadata={"reason": msg},
            )
            return {"success": False, "status": "REJECTED", "error": msg}

        # ── Step 2: Compute content hash ─────────────────────────────────
        content_hash = hashlib.sha256(note.verified_text.encode("utf-8")).hexdigest()

        # ── Step 3: Idempotency check ────────────────────────────────────
        if not force_reindex and self._doc_repo.is_indexed(note_id, content_hash):
            duration_ms = (time.time() - start_time) * 1000
            global_rag_audit_repository.log(
                RAGAuditEvent.INDEX_SKIPPED,
                note_id=note_id,
                user_id=user_id,
                duration_ms=duration_ms,
                status="skipped",
                metadata={"reason": "content hash unchanged"},
            )
            logger.info(f"IngestionService: Note {note_id} already indexed with same content — skipped")
            existing_doc = self._doc_repo.get_by_note_id(note_id)
            return {
                "success": True,
                "status": "ALREADY_INDEXED",
                "note_id": note_id,
                "chunk_count": existing_doc.chunk_count if existing_doc else 0,
                "skipped": True,
            }

        # ── Step 4: Determine version ────────────────────────────────────
        version = self._doc_repo.get_next_version(note_id)

        # ── Step 5: Remove existing chunks (reindex) ─────────────────────
        try:
            store = get_vector_store(embedding_dim=self._embedder.dimension)
            deleted = store.delete_by_note_id(note_id)
            if deleted > 0:
                logger.info(f"IngestionService: Removed {deleted} existing chunks for note {note_id}")
        except Exception as e:
            logger.warning(f"IngestionService: Failed to delete existing chunks: {e}")

        # ── Step 6: Create rag_document record (PENDING) ─────────────────
        doc_id = str(uuid.uuid4())
        rag_doc = RAGDocument(
            id=doc_id,
            note_id=note_id,
            source_version=version,
            content_hash=content_hash,
            status=RAGDocumentStatus.PENDING,
            ocr_run_id=note.ocr_run_id,
            source_file_id=note.source_file_id,
            verified_by=note.verified_by,
            verified_at=note.verified_at,
            organization_id=note.organization_id,
        )
        self._doc_repo.upsert(rag_doc)

        # ── Step 7: Chunk the document ────────────────────────────────────
        try:
            chunks = self._chunker.chunk_note(note, rag_document_id=doc_id)
            if not chunks:
                raise ValueError("No valid chunks produced")
        except Exception as e:
            self._doc_repo.mark_failed(note_id, f"Chunking failed: {e}")
            logger.error(f"IngestionService: Chunking failed for note {note_id}: {e}")
            global_rag_audit_repository.log(
                RAGAuditEvent.INDEX_FAILED, note_id=note_id, user_id=user_id,
                status="failure", metadata={"stage": "chunking", "error": str(e)},
            )
            return {"success": False, "status": "CHUNKING_FAILED", "error": str(e)}

        # ── Step 8: Generate embeddings ───────────────────────────────────
        try:
            chunks = self._embedder.embed_chunks(chunks)
        except Exception as e:
            self._doc_repo.mark_failed(note_id, f"Embedding failed: {e}")
            logger.error(f"IngestionService: Embedding failed for note {note_id}: {e}")
            global_rag_audit_repository.log(
                RAGAuditEvent.INDEX_FAILED, note_id=note_id, user_id=user_id,
                status="failure", metadata={"stage": "embedding", "error": str(e)},
            )
            return {"success": False, "status": "EMBEDDING_FAILED", "error": str(e)}

        # ── Step 9: Store chunks in vector store ──────────────────────────
        try:
            store.upsert_chunks(chunks)
        except Exception as e:
            self._doc_repo.mark_failed(note_id, f"Vector store failed: {e}")
            logger.error(f"IngestionService: Vector store upsert failed for note {note_id}: {e}")
            global_rag_audit_repository.log(
                RAGAuditEvent.INDEX_FAILED, note_id=note_id, user_id=user_id,
                status="failure", metadata={"stage": "vector_store", "error": str(e)},
            )
            return {"success": False, "status": "STORE_FAILED", "error": str(e)}

        # ── Step 10: Mark indexed ─────────────────────────────────────────
        rag_doc.status = RAGDocumentStatus.INDEXED
        rag_doc.chunk_count = len(chunks)
        rag_doc.indexed_at = datetime.now(timezone.utc).isoformat()
        self._doc_repo.upsert(rag_doc)

        duration_ms = (time.time() - start_time) * 1000
        global_rag_audit_repository.log(
            RAGAuditEvent.INDEX_COMPLETED,
            note_id=note_id,
            user_id=user_id,
            duration_ms=duration_ms,
            status="success",
            metadata={
                "chunk_count": len(chunks),
                "version": version,
                "content_hash": content_hash[:16] + "...",
            },
        )

        logger.info(
            f"IngestionService: Indexed note {note_id} → "
            f"{len(chunks)} chunks (v{version}, {duration_ms:.0f}ms)"
        )

        return {
            "success": True,
            "status": "INDEXED",
            "note_id": note_id,
            "rag_document_id": doc_id,
            "chunk_count": len(chunks),
            "version": version,
            "duration_ms": round(duration_ms, 1),
        }

    def remove_index(self, note_id: str, user_id: str = "system") -> Dict[str, Any]:
        """
        Removes a note's RAG index. Does NOT delete the source note.

        Args:
            note_id: Note to remove from index.
            user_id: Requesting user (for audit).

        Returns:
            Result dict with deleted chunk count.
        """
        try:
            store = get_vector_store()
            deleted = store.delete_by_note_id(note_id)
            self._doc_repo.mark_removed(note_id)
            global_rag_audit_repository.log(
                RAGAuditEvent.REMOVE,
                note_id=note_id,
                user_id=user_id,
                metadata={"chunks_deleted": deleted},
            )
            logger.info(f"IngestionService: Removed RAG index for note {note_id} ({deleted} chunks)")
            return {"success": True, "note_id": note_id, "chunks_deleted": deleted}
        except Exception as e:
            logger.error(f"IngestionService: Remove failed for note {note_id}: {e}")
            return {"success": False, "error": str(e)}


# Module singleton
global_ingestion_service = IngestionService()
