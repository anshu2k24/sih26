"""
Notes Adapter
=============
Isolation layer between the RAG module and the existing notes pipeline.

CRITICAL RULES:
- This adapter is READ-ONLY. It NEVER calls update_note(), delete_note(), or create_note().
- It normalizes the existing note schema into a stable VerifiedNoteDTO.
- It does not assume every field is present — all optional fields are safely defaulted.
- It enforces that only VERIFIED notes are accessible to the RAG indexing pipeline.

Architecture:
    Existing NoteRepository (read-only access)
          ↓
    NotesAdapter
          ↓
    VerifiedNoteDTO
          ↓
    RAG Ingestion Service
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

logger = logging.getLogger("ertmac.rag.adapters.notes")


@dataclass
class VerifiedNoteDTO:
    """
    Stable data transfer object for a verified note.
    The RAG module exclusively uses this DTO — never raw note dicts.
    """
    note_id: str
    title: str
    verified_text: str
    raw_ocr_text: Optional[str] = None
    structured_data: Dict[str, Any] = field(default_factory=dict)
    verification_status: str = "VERIFIED"
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    source_file_id: Optional[str] = None
    ocr_run_id: Optional[str] = None            # latest_ocr_run_id from note
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    organization_id: Optional[str] = None


class NotesAdapter:
    """
    Read-only adapter over the existing NoteRepository.
    Translates raw note dicts into VerifiedNoteDTOs.
    """

    def __init__(self, repository=None):
        """
        Args:
            repository: An instance of NoteRepository. Defaults to the global singleton.
        """
        if repository is None:
            # Import here to avoid circular imports at module load time
            from ertmac.notes.repository import global_note_repository
            self._repo = global_note_repository
        else:
            self._repo = repository

    def get_verified_note(self, note_id: str) -> Optional[VerifiedNoteDTO]:
        """
        Fetches a note by ID and returns a VerifiedNoteDTO only if status is VERIFIED.
        Returns None if:
          - Note does not exist
          - Note is soft-deleted
          - Note is not in VERIFIED status
          - Note has empty verified_text
        """
        note = self._repo.get_note(note_id)
        if not note:
            logger.debug(f"NotesAdapter: note {note_id} not found")
            return None

        if note.get("is_deleted", False):
            logger.debug(f"NotesAdapter: note {note_id} is soft-deleted")
            return None

        if note.get("verification_status") != "VERIFIED":
            logger.info(
                f"NotesAdapter: note {note_id} rejected — "
                f"status={note.get('verification_status')} (must be VERIFIED)"
            )
            return None

        verified_text = note.get("verified_text", "") or ""
        if not verified_text.strip():
            logger.info(f"NotesAdapter: note {note_id} rejected — verified_text is empty")
            return None

        return self._build_dto(note)

    def get_note_for_ingestion_check(self, note_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns minimal note metadata for pre-ingestion checks (status check only).
        Does not return full text — used to validate eligibility before heavy operations.
        """
        note = self._repo.get_note(note_id)
        if not note or note.get("is_deleted", False):
            return None
        return {
            "note_id": note["id"],
            "verification_status": note.get("verification_status"),
            "ocr_status": note.get("ocr_status"),
            "has_verified_text": bool((note.get("verified_text") or "").strip()),
            "title": note.get("title", "Untitled"),
            "updated_at": note.get("updated_at"),
        }

    def list_verified_notes(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[VerifiedNoteDTO]:
        """
        Returns all VERIFIED notes — used for bulk indexing / reindex operations.
        """
        all_notes = self._repo.list_notes(
            limit=limit,
            offset=offset,
            status_filter="VERIFIED",
        )
        dtos = []
        for note in all_notes:
            dto = self._build_dto(note)
            if dto and dto.verified_text.strip():
                dtos.append(dto)
        return dtos

    def get_ocr_runs(self, note_id: str) -> List[Dict[str, Any]]:
        """
        Returns the OCR run history for provenance chain construction.
        Read-only access.
        """
        return self._repo.get_ocr_runs(note_id)

    # ── Private Helpers ──────────────────────────────────────────────────────

    def _build_dto(self, note: Dict[str, Any]) -> Optional[VerifiedNoteDTO]:
        """Safely normalizes a raw note dict into VerifiedNoteDTO."""
        try:
            note_id = note.get("id", "")
            if not note_id:
                return None

            # Extract organization_id safely from nested metadata
            metadata = note.get("metadata") or {}
            org_id = metadata.get("organization_id")

            return VerifiedNoteDTO(
                note_id=note_id,
                title=note.get("title") or "Untitled Note",
                verified_text=note.get("verified_text") or "",
                raw_ocr_text=note.get("raw_ocr_text"),
                structured_data=note.get("structured_data") or {},
                verification_status=note.get("verification_status", "NEEDS_REVIEW"),
                verified_by=note.get("verified_by"),
                verified_at=note.get("verified_at"),
                source_file_id=note.get("source_file_id"),
                ocr_run_id=note.get("latest_ocr_run_id"),
                created_at=note.get("created_at"),
                updated_at=note.get("updated_at"),
                organization_id=org_id,
            )
        except Exception as e:
            logger.error(f"NotesAdapter._build_dto error for note {note.get('id')}: {e}")
            return None


# Module-level singleton
global_notes_adapter = NotesAdapter()
