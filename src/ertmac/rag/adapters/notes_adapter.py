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
            doc_dto = self._get_document_dto(note_id)
            if doc_dto:
                return doc_dto
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
        if not note:
            doc_dto = self._get_document_dto(note_id)
            if doc_dto:
                return {
                    "note_id": doc_dto.note_id,
                    "verification_status": "VERIFIED",
                    "ocr_status": "COMPLETED",
                    "has_verified_text": True,
                    "title": doc_dto.title,
                    "updated_at": doc_dto.updated_at,
                }
            return None
        if note.get("is_deleted", False):
            return None
        return {
            "note_id": note["id"],
            "verification_status": note.get("verification_status"),
            "ocr_status": note.get("ocr_status"),
            "has_verified_text": bool((note.get("verified_text") or "").strip()),
            "title": note.get("title", "Untitled"),
            "updated_at": note.get("updated_at"),
        }

    def _get_document_dto(self, doc_id: str) -> Optional[VerifiedNoteDTO]:
        """Fetches and builds DTO from digital document records (PDF, DOCX, TXT, CSV)."""
        try:
            from ertmac.auth.supabase_client import get_supabase_admin
            from ertmac.documents.uploader import _in_memory_docs
            from ertmac.documents.extractor import extract_text_from_file

            doc = None
            db = get_supabase_admin()
            if db:
                try:
                    res = db.table("documents").select("*").eq("id", doc_id).execute()
                    if res.data and len(res.data) > 0:
                        doc = res.data[0]
                except Exception:
                    pass

            if not doc:
                doc = _in_memory_docs.get(doc_id)

            if not doc:
                return None

            storage_path = doc.get("storage_path")
            doc_type = doc.get("document_type") or "PDF"
            text_content = ""
            if storage_path:
                text_content, _, _ = extract_text_from_file(storage_path, doc_type)

            if not text_content or not text_content.strip():
                return None

            return VerifiedNoteDTO(
                note_id=str(doc["id"]),
                title=doc.get("filename") or "Digital Document",
                verified_text=text_content.strip(),
                raw_ocr_text=text_content.strip(),
                structured_data={"filename": doc.get("filename"), "doc_type": doc_type},
                verification_status="VERIFIED",
                created_at=doc.get("created_at"),
                updated_at=doc.get("updated_at"),
                organization_id=doc.get("organization_id"),
            )
        except Exception as e:
            logger.error(f"NotesAdapter._get_document_dto error for {doc_id}: {e}")
            return None

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
