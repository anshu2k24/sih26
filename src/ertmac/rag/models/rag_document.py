"""
RAG Document Model
Tracks the indexing state of a verified note in the RAG system.
References the source note by note_id — does not duplicate note content.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class RAGDocumentStatus(str, Enum):
    PENDING   = "PENDING"
    INDEXED   = "INDEXED"
    FAILED    = "FAILED"
    REMOVED   = "REMOVED"


@dataclass
class RAGDocument:
    """
    Represents a note's presence in the RAG index.

    Provenance chain:
        RAGDocument → note_id → handwritten_notes.id
                    → ocr_run_id → ocr_runs.id
                    → source_file_id → stored image file
    """
    note_id: str
    source_version: int                         # increments on each index/reindex
    content_hash: str                           # SHA-256 of verified_text (idempotency)
    status: RAGDocumentStatus = RAGDocumentStatus.PENDING

    # Populated on successful indexing
    id: Optional[str] = None
    chunk_count: int = 0
    indexed_at: Optional[str] = None
    updated_at: Optional[str] = None
    error_message: Optional[str] = None

    # Provenance references (copied from source note at index time, never overwritten)
    ocr_run_id: Optional[str] = None
    source_file_id: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None

    # Access control preparation (for future multi-tenant filtering)
    organization_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "note_id": self.note_id,
            "source_version": self.source_version,
            "content_hash": self.content_hash,
            "status": self.status.value,
            "chunk_count": self.chunk_count,
            "indexed_at": self.indexed_at,
            "updated_at": self.updated_at,
            "error_message": self.error_message,
            "ocr_run_id": self.ocr_run_id,
            "source_file_id": self.source_file_id,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at,
            "organization_id": self.organization_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RAGDocument":
        return cls(
            id=data.get("id"),
            note_id=data["note_id"],
            source_version=data.get("source_version", 1),
            content_hash=data.get("content_hash", ""),
            status=RAGDocumentStatus(data.get("status", "PENDING")),
            chunk_count=data.get("chunk_count", 0),
            indexed_at=data.get("indexed_at"),
            updated_at=data.get("updated_at"),
            error_message=data.get("error_message"),
            ocr_run_id=data.get("ocr_run_id"),
            source_file_id=data.get("source_file_id"),
            verified_by=data.get("verified_by"),
            verified_at=data.get("verified_at"),
            organization_id=data.get("organization_id"),
        )
