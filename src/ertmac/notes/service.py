"""
PS121 Handwritten Notes OCR — Core Business Service
Orchestrates end-to-end handwritten document lifecycle:
Upload -> File Validation -> Storage -> Preprocessing -> OCR Provider -> Normalization -> Structured Extraction -> Human Verification -> Full Provenance & Audit
"""

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

from ertmac.ocr.service import OCRService, global_ocr_service
from ertmac.notes.validator import FileValidator, FileValidationError
from ertmac.notes.normalizer import TextNormalizer
from ertmac.notes.extractor import StructuredExtractor
from ertmac.notes.storage import NoteStorageManager, global_storage_manager
from ertmac.notes.repository import NoteRepository, global_note_repository
from ertmac.audit.logger import global_audit_service

logger = logging.getLogger("ertmac.notes.service")


class HandwrittenNotesService:
    """
    Core domain service implementing the SIH 2026 PS121 Handwritten Notes OCR Pipeline.
    """

    def __init__(
        self,
        ocr_service: Optional[OCRService] = None,
        repository: Optional[NoteRepository] = None,
        storage: Optional[NoteStorageManager] = None,
    ):
        self.ocr_service = ocr_service or global_ocr_service
        self.repo = repository or global_note_repository
        self.storage = storage or global_storage_manager

    async def ingest_handwritten_note(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: str = "system",
        organization_id: Optional[str] = None,
        title_override: Optional[str] = None,
        ocr_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes complete ingestion pipeline:
        1. Multi-layer file validation (magic bytes, MIME, size, dimension)
        2. Idempotency check via SHA-256
        3. Local & Object Storage preservation of original image
        4. Preprocessing & OCR transcription
        5. Normalization & Structured Extraction
        6. Note & OCR Run persistence
        7. Audit logging
        """
        start_time = time.time()

        # Step 1: Validation
        validation_info = FileValidator.validate(file_bytes=file_bytes, filename=filename)

        note_id = str(uuid.uuid4())

        # Step 2: Store original image for provenance
        stored_file = self.storage.store_file(
            file_bytes=file_bytes,
            filename=filename,
            note_id=note_id,
            mime_type=validation_info["mime_type"],
        )

        # Idempotency check: see if identical file is already active
        existing = self.repo.find_by_checksum(stored_file["checksum"])
        if existing:
            self.repo.log_audit(
                action="NOTE_UPLOAD_DUPLICATE",
                note_id=existing["id"],
                user_id=user_id,
                details={"filename": filename, "checksum": stored_file["checksum"]},
            )
            return {
                "status": "DUPLICATE",
                "message": f"Identical file already ingested (Note ID: {existing['id']})",
                "note": existing,
                "is_duplicate": True,
            }

        # Step 3: Create initial note record
        note_record = self.repo.create_note({
            "id": note_id,
            "title": title_override or f"Handwritten Note — {filename}",
            "source_file_id": stored_file["file_id"],
            "storage_path": stored_file["storage_path"],
            "public_url": stored_file["public_url"],
            "ocr_status": "PROCESSING",
            "verification_status": "NEEDS_REVIEW",
            "metadata": {
                "validation": validation_info,
                "storage": stored_file,
                "checksum": stored_file["checksum"],
                "organization_id": organization_id,
            },
            "created_by": user_id,
        })

        self.repo.log_audit("note.created", note_id, user_id, {"filename": filename})
        self.repo.log_audit("note.ocr.started", note_id, user_id, {"provider": self.ocr_service.provider.provider_name})

        # Step 4: Execute OCR
        try:
            ocr_result = await self.ocr_service.process_image(
                image_bytes=file_bytes,
                filename=filename,
                mime_type=validation_info["mime_type"],
                model=ocr_model,
            )

            # Step 5: Normalize and extract structured entities
            normalized = TextNormalizer.normalize(ocr_result.normalized_text or ocr_result.raw_text)
            structured = StructuredExtractor.extract_structured(
                text=normalized,
                fallback_title=title_override or filename,
            )

            # Record OCR Run #1
            ocr_run = self.repo.record_ocr_run({
                "note_id": note_id,
                "provider": ocr_result.provider,
                "model": ocr_result.model,
                "status": "COMPLETED",
                "confidence": ocr_result.confidence,
                "raw_result": ocr_result.to_dict(),
                "normalized_text": normalized,
                "processing_time_ms": ocr_result.processing_time_ms,
                "attempt": 1,
            })

            # Update Note with results
            updated_note = self.repo.update_note(note_id, {
                "title": title_override or structured.get("title") or note_record["title"],
                "raw_ocr_text": ocr_result.raw_text,
                "verified_text": normalized,  # Initial draft for reviewer
                "ocr_status": "COMPLETED",
                "verification_status": "NEEDS_REVIEW",
                "confidence": ocr_result.confidence,
                "confidence_level": ocr_result.confidence_level.value,
                "latest_ocr_run_id": ocr_run["id"],
                "structured_data": structured,
            })

            self.repo.log_audit(
                "note.ocr.completed",
                note_id,
                user_id,
                {
                    "ocr_run_id": ocr_run["id"],
                    "provider": ocr_result.provider,
                    "duration_ms": ocr_result.processing_time_ms,
                },
            )

            return {
                "success": True,
                "status": "NEEDS_REVIEW",
                "note": updated_note,
                "ocr_run": ocr_run,
                "provenance": {
                    "source_file_id": stored_file["file_id"],
                    "ocr_run_id": ocr_run["id"],
                    "checksum": stored_file["checksum"],
                },
            }

        except Exception as e:
            logger.error(f"OCR processing failed for note {note_id}: {e}", exc_info=True)
            failed_run = self.repo.record_ocr_run({
                "note_id": note_id,
                "provider": self.ocr_service.provider.provider_name,
                "model": ocr_model or self.ocr_service.provider.default_model,
                "status": "FAILED",
                "error": str(e),
                "attempt": 1,
            })

            updated_note = self.repo.update_note(note_id, {
                "ocr_status": "FAILED",
                "latest_ocr_run_id": failed_run["id"],
            })

            self.repo.log_audit("note.ocr.failed", note_id, user_id, {"error": str(e)})

            return {
                "success": False,
                "status": "OCR_FAILED",
                "error": f"OCR processing failed: {e}",
                "note": updated_note,
            }

    async def verify_note(
        self,
        note_id: str,
        verified_text: str,
        user_id: str,
        title: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Promotes draft OCR note to TRUSTED VERIFIED status.
        Crucial principle: NEVER overwrite raw_ocr_text.
        """
        note = self.repo.get_note(note_id)
        if not note:
            return None

        # Re-extract structured entities from verified text
        normalized_verified = TextNormalizer.normalize(verified_text)
        structured = StructuredExtractor.extract_structured(
            text=normalized_verified,
            fallback_title=title or note["title"],
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        updates = {
            "title": title or structured["title"] or note["title"],
            "verified_text": normalized_verified,
            "verification_status": "VERIFIED",
            "verified_by": user_id,
            "verified_at": now_iso,
            "structured_data": structured,
        }

        updated = self.repo.update_note(note_id, updates)
        self.repo.log_audit("note.verified", note_id, user_id, {
            "verified_at": now_iso,
            "char_count": len(normalized_verified),
        })

        return updated

    async def reject_note(
        self,
        note_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Marks a note as REJECTED when OCR result is unsalvageable.
        """
        note = self.repo.get_note(note_id)
        if not note:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        updates = {
            "verification_status": "REJECTED",
            "verified_by": user_id,
            "verified_at": now_iso,
        }

        updated = self.repo.update_note(note_id, updates)
        self.repo.log_audit("note.rejected", note_id, user_id, {
            "rejected_at": now_iso,
        })

        return updated

    async def retry_ocr(
        self,
        note_id: str,
        user_id: str,
        ocr_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retries OCR for a note using stored original image without destroying prior run history.
        """
        note = self.repo.get_note(note_id)
        if not note:
            return {"success": False, "error": f"Note '{note_id}' not found."}

        # Fetch original image bytes
        storage_path = note.get("storage_path")
        file_bytes = self.storage.get_file_bytes(storage_path)
        if not file_bytes:
            return {"success": False, "error": "Original image file could not be retrieved from storage."}

        # Determine attempt number
        previous_runs = self.repo.get_ocr_runs(note_id)
        attempt_no = len(previous_runs) + 1

        self.repo.update_note(note_id, {"ocr_status": "PROCESSING"})
        self.repo.log_audit("note.ocr.retried", note_id, user_id, {"attempt": attempt_no})

        try:
            ocr_result = await self.ocr_service.process_image(
                image_bytes=file_bytes,
                filename=note.get("metadata", {}).get("storage", {}).get("filename", f"note_{note_id}.jpg"),
                model=ocr_model,
            )

            normalized = TextNormalizer.normalize(ocr_result.normalized_text or ocr_result.raw_text)
            structured = StructuredExtractor.extract_structured(normalized, fallback_title=note["title"])

            ocr_run = self.repo.record_ocr_run({
                "note_id": note_id,
                "provider": ocr_result.provider,
                "model": ocr_result.model,
                "status": "COMPLETED",
                "confidence": ocr_result.confidence,
                "raw_result": ocr_result.to_dict(),
                "normalized_text": normalized,
                "processing_time_ms": ocr_result.processing_time_ms,
                "attempt": attempt_no,
            })

            updated_note = self.repo.update_note(note_id, {
                "raw_ocr_text": ocr_result.raw_text,
                "verified_text": normalized,
                "ocr_status": "COMPLETED",
                "verification_status": "NEEDS_REVIEW",
                "confidence": ocr_result.confidence,
                "confidence_level": ocr_result.confidence_level.value,
                "latest_ocr_run_id": ocr_run["id"],
                "structured_data": structured,
            })

            self.repo.log_audit("note.ocr.completed", note_id, user_id, {"attempt": attempt_no, "run_id": ocr_run["id"]})

            return {"success": True, "note": updated_note, "ocr_run": ocr_run}

        except Exception as e:
            failed_run = self.repo.record_ocr_run({
                "note_id": note_id,
                "provider": self.ocr_service.provider.provider_name,
                "model": ocr_model or self.ocr_service.provider.default_model,
                "status": "FAILED",
                "error": str(e),
                "attempt": attempt_no,
            })

            self.repo.update_note(note_id, {
                "ocr_status": "FAILED",
                "latest_ocr_run_id": failed_run["id"],
            })

            return {"success": False, "error": f"OCR retry failed: {e}"}

    def save_draft(self, note_id: str, draft_text: str, user_id: str, title: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Saves reviewer's draft edits without marking note as fully verified."""
        updates: Dict[str, Any] = {"verified_text": draft_text}
        if title:
            updates["title"] = title
        
        updated = self.repo.update_note(note_id, updates)
        if updated:
            self.repo.log_audit("note.updated", note_id, user_id, {"type": "draft_save"})
        return updated

    def export_note(self, note_id: str, export_format: str = "json") -> Tuple[Optional[str], str]:
        """
        Exports verified note in TXT or JSON format.
        Returns: (content_string, content_type)
        """
        note = self.repo.get_note(note_id)
        if not note:
            return None, "text/plain"

        fmt = export_format.lower().strip()
        if fmt == "txt":
            content = (
                f"TITLE: {note.get('title')}\n"
                f"STATUS: {note.get('verification_status')}\n"
                f"VERIFIED AT: {note.get('verified_at') or 'N/A'}\n"
                f"VERIFIED BY: {note.get('verified_by') or 'N/A'}\n"
                f"SOURCE FILE ID: {note.get('source_file_id')}\n"
                f"{'='*60}\n\n"
                f"{note.get('verified_text') or note.get('raw_ocr_text')}\n"
            )
            return content, "text/plain; charset=utf-8"

        # JSON Export
        export_payload = {
            "id": note["id"],
            "title": note["title"],
            "status": note["verification_status"],
            "ocr_status": note["ocr_status"],
            "raw_ocr_text": note["raw_ocr_text"],
            "verified_text": note["verified_text"],
            "structured_data": note.get("structured_data", {}),
            "provenance": {
                "source_file_id": note["source_file_id"],
                "ocr_run_id": note["latest_ocr_run_id"],
                "checksum": note.get("metadata", {}).get("checksum"),
                "verified_by": note.get("verified_by"),
                "verified_at": note.get("verified_at"),
                "created_at": note["created_at"],
            },
        }
        import json
        return json.dumps(export_payload, indent=2), "application/json"

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Calculates live dashboard statistics across all notes."""
        notes = self.repo.list_notes(limit=1000)
        total = len(notes)
        processing = sum(1 for n in notes if n.get("ocr_status") == "PROCESSING")
        needs_review = sum(1 for n in notes if n.get("verification_status") == "NEEDS_REVIEW" and n.get("ocr_status") == "COMPLETED")
        verified = sum(1 for n in notes if n.get("verification_status") == "VERIFIED")
        failed = sum(1 for n in notes if n.get("ocr_status") == "FAILED")

        verification_rate = (verified / total * 100) if total > 0 else 0.0

        return {
            "total_notes": total,
            "processing": processing,
            "needs_review": needs_review,
            "verified": verified,
            "failed": failed,
            "verification_rate_pct": round(verification_rate, 1),
            "active_provider": self.ocr_service.provider.provider_name,
            "active_model": self.ocr_service.provider.default_model,
        }


# Global singleton instance
global_handwritten_notes_service = HandwrittenNotesService()
