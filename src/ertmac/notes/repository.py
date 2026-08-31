"""
PS121 Handwritten Notes OCR — Database Repository
Handles CRUD operations for:
- handwritten_notes (lifecycle, raw vs verified text, provenance)
- ocr_runs (immutable OCR processing run history)
- ocr_audit_logs (audit log trails)

Supports dual backend: Supabase PostgreSQL when connected, and persistent in-memory/JSON store.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from ertmac.auth.supabase_client import get_supabase_admin, is_supabase_configured

logger = logging.getLogger("ertmac.notes.repository")


class NoteRepository:
    """
    Repository for Handwritten Notes and OCR Run tracking.
    """

    def __init__(self):
        # In-memory storage buffers
        self._notes: Dict[str, Dict[str, Any]] = {}
        self._runs: Dict[str, List[Dict[str, Any]]] = {}
        self._audit_logs: List[Dict[str, Any]] = []

    def create_note(self, note_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new handwritten note record."""
        note_id = note_data.get("id") or str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        
        record = {
            "id": note_id,
            "title": note_data.get("title", "Untitled Handwritten Note"),
            "raw_ocr_text": note_data.get("raw_ocr_text", ""),
            "verified_text": note_data.get("verified_text", ""),
            "source": "handwritten",
            "source_file_id": note_data.get("source_file_id", ""),
            "storage_path": note_data.get("storage_path", ""),
            "public_url": note_data.get("public_url", ""),
            "ocr_status": note_data.get("ocr_status", "UPLOADED"),
            "verification_status": note_data.get("verification_status", "NEEDS_REVIEW"),
            "confidence": note_data.get("confidence"),
            "confidence_level": note_data.get("confidence_level", "UNKNOWN"),
            "latest_ocr_run_id": note_data.get("latest_ocr_run_id"),
            "structured_data": note_data.get("structured_data", {}),
            "metadata": note_data.get("metadata", {}),
            "created_by": note_data.get("created_by", "system"),
            "verified_by": note_data.get("verified_by"),
            "created_at": note_data.get("created_at", now_iso),
            "updated_at": now_iso,
            "verified_at": note_data.get("verified_at"),
            "is_deleted": False,
        }

        self._notes[note_id] = record

        # Try saving to Supabase if configured
        if is_supabase_configured():
            try:
                client = get_supabase_admin()
                client.table("handwritten_notes").upsert(record).execute()
            except Exception as e:
                logger.debug(f"Supabase write for note {note_id} skipped: {e}")

        return record

    def update_note(self, note_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates specific fields of an existing note."""
        note = self._notes.get(note_id)
        if not note or note.get("is_deleted", False):
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        for k, v in updates.items():
            if k != "id":
                note[k] = v
        note["updated_at"] = now_iso

        self._notes[note_id] = note

        if is_supabase_configured():
            try:
                client = get_supabase_admin()
                client.table("handwritten_notes").update(updates).eq("id", note_id).execute()
            except Exception as e:
                logger.debug(f"Supabase update for note {note_id} skipped: {e}")

        return note

    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single note by ID."""
        note = self._notes.get(note_id)
        if note and not note.get("is_deleted", False):
            return note

        if is_supabase_configured():
            try:
                client = get_supabase_admin()
                res = client.table("handwritten_notes").select("*").eq("id", note_id).execute()
                if res.data:
                    self._notes[note_id] = res.data[0]
                    return res.data[0]
            except Exception as e:
                logger.debug(f"Supabase fetch error for note {note_id}: {e}")

        return None

    def find_by_checksum(self, checksum: str) -> Optional[Dict[str, Any]]:
        """Finds active note matching SHA-256 checksum for idempotency."""
        for note in self._notes.values():
            if not note.get("is_deleted") and note.get("metadata", {}).get("checksum") == checksum:
                return note
        return None

    def list_notes(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists notes with optional filtering and search."""
        active = [n for n in self._notes.values() if not n.get("is_deleted", False)]
        
        if status_filter:
            active = [n for n in active if n.get("verification_status") == status_filter or n.get("ocr_status") == status_filter]

        if search_query:
            q = search_query.lower()
            active = [
                n for n in active
                if q in n.get("title", "").lower()
                or q in n.get("verified_text", "").lower()
                or q in n.get("raw_ocr_text", "").lower()
                or any(q in t.lower() for t in n.get("structured_data", {}).get("tags", []))
            ]

        # Sort descending by created_at
        active.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return active[offset : offset + limit]

    def delete_note(self, note_id: str) -> bool:
        """Soft deletes a note."""
        note = self._notes.get(note_id)
        if not note:
            return False
        note["is_deleted"] = True
        note["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        if is_supabase_configured():
            try:
                client = get_supabase_admin()
                client.table("handwritten_notes").update({"is_deleted": True}).eq("id", note_id).execute()
            except Exception as e:
                logger.debug(f"Supabase delete for note {note_id} skipped: {e}")
        return True

    # ── OCR RUNS HISTORY ──────────────────────────────────────────

    def record_ocr_run(self, run_data: Dict[str, Any]) -> Dict[str, Any]:
        """Appends an immutable OCR run record to processing history."""
        run_id = run_data.get("id") or str(uuid.uuid4())
        note_id = run_data.get("note_id")
        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            "id": run_id,
            "note_id": note_id,
            "provider": run_data.get("provider", "unknown"),
            "model": run_data.get("model", "unknown"),
            "status": run_data.get("status", "COMPLETED"),
            "confidence": run_data.get("confidence"),
            "raw_result": run_data.get("raw_result", {}),
            "normalized_text": run_data.get("normalized_text", ""),
            "processing_time_ms": run_data.get("processing_time_ms", 0),
            "error": run_data.get("error"),
            "attempt": run_data.get("attempt", 1),
            "created_at": run_data.get("created_at", now_iso),
            "completed_at": run_data.get("completed_at", now_iso),
        }

        if note_id not in self._runs:
            self._runs[note_id] = []
        self._runs[note_id].append(record)

        if is_supabase_configured():
            try:
                client = get_supabase_admin()
                client.table("ocr_runs").insert(record).execute()
            except Exception as e:
                logger.debug(f"Supabase insert ocr_run skipped: {e}")

        return record

    def get_ocr_runs(self, note_id: str) -> List[Dict[str, Any]]:
        """Returns processing history of all OCR runs for a note."""
        runs = self._runs.get(note_id, [])
        runs.sort(key=lambda x: x.get("attempt", 1))
        return runs

    # ── AUDIT LOGS ───────────────────────────────────────────────

    def log_audit(self, action: str, note_id: str, user_id: str, details: Dict[str, Any]):
        """Records note-specific audit event."""
        entry = {
            "id": str(uuid.uuid4()),
            "note_id": note_id,
            "action": action,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        }
        self._audit_logs.append(entry)

    def get_audit_logs(self, note_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns audit logs."""
        if note_id:
            return [a for a in self._audit_logs if a.get("note_id") == note_id]
        return list(self._audit_logs)


# Global singleton instance
global_note_repository = NoteRepository()
