"""
PS26121 eRTMAC-NWIS — Extracted Event Verification & Promotion Engine
Allows Drilling Engineers / Administrators to review extracted events.
When verified, promotes the event to verified historical knowledge records.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from ertmac.auth.supabase_client import get_supabase_admin
from ertmac.audit.logger import global_audit_service

logger = logging.getLogger("ertmac.documents.verifier")

_in_memory_extracted_events: Dict[str, Dict[str, Any]] = {}


class DocumentVerificationEngine:
    """Manages verification, rejection, and promotion of extracted events to historical DDR database."""

    @staticmethod
    def save_extracted_events(document_id: str, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Saves extracted events to DB / memory."""
        saved_list: List[Dict[str, Any]] = []
        db = get_supabase_admin()

        for evt in events:
            evt_id = str(evt.get("id") or f"EXT_{uuid.uuid4().hex[:8].upper()}")
            evt["id"] = evt_id
            _in_memory_extracted_events[evt_id] = evt

            if db:
                try:
                    db_payload = {
                        "document_id": document_id if len(document_id) == 36 else None,
                        "organization_id": evt.get("organization_id", "00000000-0000-0000-0000-000000000001"),
                        "well_id": evt.get("well_id"),
                        "event_type": evt.get("event_type"),
                        "event_domain": evt.get("event_domain"),
                        "onset_md": evt.get("onset_md"),
                        "onset_tvd": evt.get("onset_tvd"),
                        "evidence_text": evt.get("evidence_text"),
                        "mitigation_text": evt.get("mitigation_text"),
                        "resolution_text": evt.get("resolution_text"),
                        "confidence": evt.get("confidence"),
                        "verification_status": evt.get("verification_status", "EXTRACTED"),
                    }
                    res = db.table("extracted_events").insert(db_payload).execute()
                    if res.data and len(res.data) > 0:
                        db_row = res.data[0]
                        evt_id = str(db_row["id"])
                        evt["id"] = evt_id
                        _in_memory_extracted_events[evt_id] = db_row
                except Exception as e:
                    logger.warning(f"Failed to persist extracted event to DB: {e}")

            saved_list.append(evt)

        # Update document verification_status to REVIEW_REQUIRED if events were extracted
        if events and db and len(document_id) == 36:
            try:
                db.table("documents").update({
                    "extraction_status": "EXTRACTED",
                    "verification_status": "REVIEW_REQUIRED"
                }).eq("id", document_id).execute()
            except Exception as e:
                logger.warning(f"Failed to update document status: {e}")

        return saved_list

    @staticmethod
    def get_events_for_document(document_id: str) -> List[Dict[str, Any]]:
        """Fetches extracted events for a specific document."""
        db = get_supabase_admin()
        if db:
            try:
                res = (
                    db.table("extracted_events")
                    .select("*")
                    .eq("document_id", document_id)
                    .order("created_at", desc=False)
                    .execute()
                )
                if res.data is not None and len(res.data) > 0:
                    return res.data
            except Exception as e:
                logger.warning(f"Failed to fetch extracted events from DB: {e}")

        return [e for e in _in_memory_extracted_events.values() if e.get("document_id") == document_id]

    @staticmethod
    def verify_event(event_id: str, verifier_user_id: str, verifier_role: str = "DRILLING_ENGINEER") -> Optional[Dict[str, Any]]:
        """
        Marks an extracted event as VERIFIED and promotes it to historical DDR events repository.
        """
        now = datetime.now(timezone.utc).isoformat()
        clean_verifier = verifier_user_id if len(verifier_user_id) == 36 and verifier_user_id != "00000000-0000-0000-0000-000000000001" else None

        evt = _in_memory_extracted_events.get(event_id)
        if evt:
            evt["verification_status"] = "VERIFIED"
            evt["verified_by"] = verifier_user_id
            evt["verified_at"] = now

        db = get_supabase_admin()
        if db:
            try:
                updates = {
                    "verification_status": "VERIFIED",
                    "verified_at": now,
                }
                if clean_verifier:
                    updates["verified_by"] = clean_verifier

                res = db.table("extracted_events").update(updates).eq("id", event_id).execute()
                if res.data and len(res.data) > 0:
                    evt = res.data[0]

                # Promote to historical_ddr_events
                if evt:
                    ddr_id = f"EP_DOC_{uuid.uuid4().hex[:6].upper()}"
                    db.table("historical_ddr_events").insert({
                        "id": ddr_id,
                        "wellbore_id": evt.get("well_id", "15/9-F-14"),
                        "organization_id": evt.get("organization_id", "00000000-0000-0000-0000-000000000001"),
                        "event_type": evt.get("event_type", "Extracted DDR Event"),
                        "event_domain": evt.get("event_domain", "DRILLING_OPERATIONS"),
                        "onset_md": evt.get("onset_md", 2500.0),
                        "onset_tvd": evt.get("onset_tvd"),
                        "primary_evidence": evt.get("evidence_text", "Extracted evidence from uploaded report"),
                        "mitigation_text": evt.get("mitigation_text", "Remedial action recorded"),
                        "resolution_text": evt.get("resolution_text", "Resolution logged"),
                        "primary_source_record": f"Document ID: {evt.get('document_id', 'N/A')}",
                        "is_verified": True,
                    }).execute()
                    logger.info(f"Promoted verified event {event_id} to historical_ddr_events as {ddr_id}")
            except Exception as e:
                logger.error(f"Failed to verify event in DB: {e}")

        # Audit log
        global_audit_service.log_event(
            actor_id=verifier_user_id,
            actor_role=verifier_role,
            action="DOCUMENT_EVENT_VERIFIED",
            resource_type="EXTRACTED_EVENT",
            resource_id=event_id,
            payload={"verification_status": "VERIFIED"},
        )

        return evt

    @staticmethod
    def reject_event(event_id: str, verifier_user_id: str, verifier_role: str = "DRILLING_ENGINEER") -> Optional[Dict[str, Any]]:
        """Marks an extracted event as REJECTED."""
        now = datetime.now(timezone.utc).isoformat()
        evt = _in_memory_extracted_events.get(event_id)
        if evt:
            evt["verification_status"] = "REJECTED"
            evt["verified_at"] = now

        db = get_supabase_admin()
        if db:
            try:
                db.table("extracted_events").update({
                    "verification_status": "REJECTED",
                    "verified_at": now,
                }).eq("id", event_id).execute()
            except Exception as e:
                logger.error(f"Failed to reject event in DB: {e}")

        global_audit_service.log_event(
            actor_id=verifier_user_id,
            actor_role=verifier_role,
            action="DOCUMENT_EVENT_REJECTED",
            resource_type="EXTRACTED_EVENT",
            resource_id=event_id,
            payload={"verification_status": "REJECTED"},
        )

        return evt
