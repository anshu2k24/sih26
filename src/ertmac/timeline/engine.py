"""
PS26121 eRTMAC-NWIS — Operational Timeline Engine
Aggregates well operational timeline events across telemetry stream milestones,
alerts, document verifications, reports, and manual shift notes with depth positioning.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from ertmac.auth.supabase_client import get_supabase_admin
from ertmac.alerts.engine import global_alert_engine
from ertmac.audit.logger import global_audit_service
from ertmac.documents.verifier import DocumentVerificationEngine

logger = logging.getLogger("ertmac.timeline.engine")

_in_memory_timeline_notes: List[Dict[str, Any]] = []


class OperationalTimelineEngine:
    """Aggregates and sorts operational events along well MD depth and timestamp."""

    @staticmethod
    def add_shift_note(
        well_id: str,
        author_id: str,
        note_text: str,
        current_md: Optional[float] = None,
        organization_id: str = "00000000-0000-0000-0000-000000000001",
    ) -> Dict[str, Any]:
        """Adds a manual operator shift log entry to the well timeline."""
        now = datetime.now(timezone.utc).isoformat()
        evt = {
            "id": f"TL_{uuid.uuid4().hex[:8].upper()}",
            "organization_id": organization_id,
            "well_id": well_id,
            "event_category": "NOTE",
            "title": "Operator Shift Note",
            "description": note_text,
            "md_depth": current_md or 2500.0,
            "actor_id": author_id,
            "created_at": now,
        }

        _in_memory_timeline_notes.append(evt)

        db = get_supabase_admin()
        if db:
            try:
                db_payload = {
                    "organization_id": organization_id,
                    "well_id": well_id,
                    "event_category": "NOTE",
                    "title": "Operator Shift Note",
                    "description": note_text,
                    "md_depth": current_md or 2500.0,
                }
                if author_id and len(author_id) == 36 and author_id != "00000000-0000-0000-0000-000000000001":
                    db_payload["actor_user_id"] = author_id

                res = db.table("timeline_events").insert(db_payload).execute()
                if res.data and len(res.data) > 0:
                    evt["id"] = str(res.data[0]["id"])
            except Exception as e:
                logger.warning(f"Failed to insert shift note into DB: {e}")

        # Audit log
        global_audit_service.log_event(
            actor_id=author_id,
            action="TIMELINE_NOTE_ADDED",
            resource_type="TIMELINE",
            resource_id=evt["id"],
            well_id=well_id,
            organization_id=organization_id,
            payload={"note_text": note_text, "md_depth": current_md},
        )

        return evt

    @staticmethod
    def get_timeline(
        well_id: str,
        category: Optional[str] = None,
        min_md: Optional[float] = None,
        max_md: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates timeline items from:
        1. Manual shift notes (DB/memory)
        2. Active & resolved alerts for the well
        3. Verified document event episodes
        4. Audit log events for the well
        """
        aggregated: List[Dict[str, Any]] = []

        # 1. Manual shift notes
        db = get_supabase_admin()
        if db:
            try:
                res = (
                    db.table("timeline_events")
                    .select("*")
                    .eq("well_id", well_id)
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                if res.data:
                    for r in res.data:
                        aggregated.append({
                            "timeline_id": str(r["id"]),
                            "well_id": r.get("well_id"),
                            "event_category": r.get("event_category", "NOTE"),
                            "title": r.get("title", "Shift Note"),
                            "description": r.get("description", ""),
                            "md_depth": r.get("md_depth", 0.0),
                            "timestamp": r.get("created_at"),
                            "source": "OPERATOR",
                            "severity": "INFO",
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch timeline events from DB: {e}")

        # Fallback in-memory shift notes
        for note in _in_memory_timeline_notes:
            if note.get("well_id") == well_id:
                if not any(a["timeline_id"] == note["id"] for a in aggregated):
                    aggregated.append({
                        "timeline_id": note["id"],
                        "well_id": note["well_id"],
                        "event_category": note["event_category"],
                        "title": note["title"],
                        "description": note["description"],
                        "md_depth": note["md_depth"],
                        "timestamp": note["created_at"],
                        "source": "OPERATOR",
                        "severity": "INFO",
                    })

        # 2. Alerts for this well
        alerts = global_alert_engine.get_active_alerts(well_id=well_id)
        for alt in alerts:
            aggregated.append({
                "timeline_id": f"TL_ALT_{alt['alert_id']}",
                "well_id": alt["well_id"],
                "event_category": "ALERT",
                "title": f"[{alt['status']}] {alt['title']}",
                "description": alt["evidence"],
                "md_depth": alt["current_md"],
                "timestamp": alt["created_at"],
                "source": alt["source"],
                "severity": alt["severity"],
            })

        # 3. Audit log events for this well
        audit_events = global_audit_service.get_events(well_id=well_id, limit=50)
        for ae in audit_events:
            aggregated.append({
                "timeline_id": f"TL_AUD_{ae['audit_id']}",
                "well_id": ae.get("well_id", well_id),
                "event_category": "AUDIT",
                "title": f"Audit Action: {ae['action']}",
                "description": f"Actor {ae['actor_id']} on {ae['resource_type']}:{ae['resource_id']}",
                "md_depth": 0.0,
                "timestamp": ae["timestamp"],
                "source": "SYSTEM",
                "severity": "INFO",
            })

        # Apply filtering
        if category and category != "ALL":
            aggregated = [item for item in aggregated if item["event_category"] == category]
        if min_md is not None:
            aggregated = [item for item in aggregated if item["md_depth"] >= min_md]
        if max_md is not None:
            aggregated = [item for item in aggregated if item["md_depth"] <= max_md]

        # Sort by timestamp descending
        aggregated.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        return aggregated[:limit]
