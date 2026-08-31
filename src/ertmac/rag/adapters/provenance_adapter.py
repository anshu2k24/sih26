"""
Provenance Adapter
==================
Builds the full provenance chain from a RAG chunk back to the original handwritten image.

Traceability chain:
    Retrieved RAG Chunk
          ↓
    Verified Note (via note_id)
          ↓
    OCR Run (via latest_ocr_run_id)
          ↓
    Original Handwritten Image (via source_file_id / storage_path)

This adapter is READ-ONLY and never modifies existing records.
"""

import logging
from typing import Optional, Dict, Any, List

from ertmac.rag.models.search_result import ProvenanceInfo

logger = logging.getLogger("ertmac.rag.adapters.provenance")

# Module-level import so tests can patch 'ertmac.rag.adapters.provenance_adapter.global_note_repository'
try:
    from ertmac.notes.repository import global_note_repository
except Exception:
    global_note_repository = None  # type: ignore


class ProvenanceAdapter:
    """
    Reconstructs provenance information for search results and RAG answers.
    """

    def __init__(self, notes_adapter=None):
        if notes_adapter is None:
            from ertmac.rag.adapters.notes_adapter import global_notes_adapter
            self._notes_adapter = global_notes_adapter
        else:
            self._notes_adapter = notes_adapter

    def build_provenance(
        self,
        note_id: str,
        chunk_id: Optional[str] = None,
        version: int = 1,
    ) -> ProvenanceInfo:
        """
        Builds a ProvenanceInfo from a note_id.
        Safe to call even if note no longer exists — returns partial provenance.
        """
        try:
            note = None
            if self._notes_adapter and hasattr(self._notes_adapter, "_repo") and self._notes_adapter._repo:
                note = self._notes_adapter._repo.get_note(note_id)
            elif global_note_repository is not None:
                note = global_note_repository.get_note(note_id)

            if not note:
                return ProvenanceInfo(
                    note_id=note_id,
                    chunk_id=chunk_id,
                    version=version,
                    verification_status="UNKNOWN",
                )

            return ProvenanceInfo(
                note_id=note_id,
                chunk_id=chunk_id,
                source_file_id=note.get("source_file_id"),
                ocr_run_id=note.get("latest_ocr_run_id"),
                verified_by=note.get("verified_by"),
                verified_at=note.get("verified_at"),
                version=version,
                verification_status=note.get("verification_status", "UNKNOWN"),
            )
        except Exception as e:
            logger.warning(f"ProvenanceAdapter.build_provenance error for note {note_id}: {e}")
            return ProvenanceInfo(note_id=note_id, chunk_id=chunk_id, version=version)

    def get_ocr_run_provenance(self, note_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns the list of OCR runs for a note — supporting deep provenance inspection.
        """
        try:
            runs = self._notes_adapter.get_ocr_runs(note_id) if self._notes_adapter else []
            if not runs:
                return None
            latest = max(runs, key=lambda r: r.get("attempt", 1))
            return {
                "run_id": latest.get("id"),
                "provider": latest.get("provider"),
                "model": latest.get("model"),
                "status": latest.get("status"),
                "attempt": latest.get("attempt"),
                "confidence": latest.get("confidence"),
                "completed_at": latest.get("completed_at"),
            }
        except Exception as e:
            logger.warning(f"ProvenanceAdapter.get_ocr_run_provenance error: {e}")
            return None


# Module-level singleton
global_provenance_adapter = ProvenanceAdapter()
