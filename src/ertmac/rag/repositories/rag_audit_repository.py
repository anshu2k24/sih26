"""
RAG Audit Repository
=====================
Write-only audit log for RAG operations.
Records events: index, search, query, reindex, remove.

Does NOT log:
  - API secrets
  - Full note content
  - Embedding vectors
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

logger = logging.getLogger("ertmac.rag.repositories.audit")

# Standard RAG audit event types
class RAGAuditEvent:
    INDEX_STARTED    = "rag.index.started"
    INDEX_COMPLETED  = "rag.index.completed"
    INDEX_FAILED     = "rag.index.failed"
    INDEX_SKIPPED    = "rag.index.skipped"
    SEARCH           = "rag.search"
    QUERY            = "rag.query"
    REINDEX          = "rag.reindex"
    REMOVE           = "rag.remove"
    HEALTH_CHECK     = "rag.health_check"


class RAGAuditRepository:
    """Append-only in-memory audit log for RAG operations."""

    def __init__(self):
        self._events: List[Dict[str, Any]] = []

    def log(
        self,
        event: str,
        note_id: Optional[str] = None,
        user_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Records a RAG audit event.

        Args:
            event: Event type from RAGAuditEvent constants.
            note_id: Associated note ID (if applicable).
            user_id: Requesting user ID.
            duration_ms: Operation duration in milliseconds.
            status: "success" | "failure" | "skipped".
            metadata: Additional non-sensitive context.
        """
        entry = {
            "id": str(uuid.uuid4()),
            "event": event,
            "note_id": note_id,
            "user_id": user_id,
            "duration_ms": duration_ms,
            "status": status,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._events.append(entry)
        logger.info(
            f"RAG AUDIT | {event} | note={note_id} | status={status} "
            f"| duration={duration_ms:.1f}ms" if duration_ms else
            f"RAG AUDIT | {event} | note={note_id} | status={status}"
        )

    def get_events(
        self,
        note_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Returns recent audit events, optionally filtered."""
        events = list(reversed(self._events))
        if note_id:
            events = [e for e in events if e.get("note_id") == note_id]
        if event_type:
            events = [e for e in events if e.get("event") == event_type]
        return events[:limit]


# Global singleton
global_rag_audit_repository = RAGAuditRepository()
