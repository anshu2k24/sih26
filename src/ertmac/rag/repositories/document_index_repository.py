"""
Document Index Repository
==========================
Tracks which notes have been indexed into the RAG system.

Supports dual backend:
  - Supabase PostgreSQL (rag_documents table) when configured
  - In-memory dict fallback

This repository NEVER writes to existing OCR tables.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Any

from ertmac.rag.models.rag_document import RAGDocument, RAGDocumentStatus

logger = logging.getLogger("ertmac.rag.repositories.document_index")


class DocumentIndexRepository:
    """Tracks RAG indexing state for each verified note."""

    def __init__(self):
        self._index: Dict[str, RAGDocument] = {}  # note_id -> RAGDocument

    def get_by_note_id(self, note_id: str) -> Optional[RAGDocument]:
        """Returns current indexing state for a note, or None if never indexed."""
        return self._index.get(note_id)

    def is_indexed(self, note_id: str, content_hash: str) -> bool:
        """
        Returns True if the note is currently indexed with this exact content hash.
        Used for idempotency — prevents duplicate indexing of unchanged content.
        """
        doc = self.get_by_note_id(note_id)
        if not doc:
            return False
        return (
            doc.status == RAGDocumentStatus.INDEXED
            and doc.content_hash == content_hash
        )

    def upsert(self, doc: RAGDocument) -> RAGDocument:
        """Creates or updates a RAGDocument record."""
        now = datetime.now(timezone.utc).isoformat()
        if not doc.id:
            doc.id = str(uuid.uuid4())
        if not doc.indexed_at and doc.status == RAGDocumentStatus.INDEXED:
            doc.indexed_at = now
        doc.updated_at = now

        self._index[doc.note_id] = doc

        # Attempt to persist to vector store metadata if available
        try:
            from ertmac.rag.vectorstore.factory import get_vector_store
            store = get_vector_store()
            if hasattr(store, "upsert_rag_document"):
                store.upsert_rag_document(doc.to_dict())
        except Exception as e:
            logger.debug(f"DocumentIndexRepository: vector store upsert skipped: {e}")

        return doc

    def mark_failed(self, note_id: str, error: str) -> None:
        """Marks a document's indexing as failed."""
        doc = self.get_by_note_id(note_id)
        if doc:
            doc.status = RAGDocumentStatus.FAILED
            doc.error_message = error
            doc.updated_at = datetime.now(timezone.utc).isoformat()
            self._index[note_id] = doc
        else:
            self._index[note_id] = RAGDocument(
                id=str(uuid.uuid4()),
                note_id=note_id,
                source_version=1,
                content_hash="",
                status=RAGDocumentStatus.FAILED,
                error_message=error,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )

    def mark_removed(self, note_id: str) -> None:
        """Marks a document as removed from the index."""
        doc = self.get_by_note_id(note_id)
        if doc:
            doc.status = RAGDocumentStatus.REMOVED
            doc.updated_at = datetime.now(timezone.utc).isoformat()
            self._index[note_id] = doc

    def get_next_version(self, note_id: str) -> int:
        """Returns the next version number for a note's index."""
        doc = self.get_by_note_id(note_id)
        if not doc:
            return 1
        return doc.source_version + 1


# Global singleton
global_document_index_repository = DocumentIndexRepository()
