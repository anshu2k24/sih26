"""
PS26121 eRTMAC-NWIS — Alert Persistence Module
Provides database storage and retrieval for operational alerts and alert notes
using Supabase, with automatic fallback to in-memory handling.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from ertmac.auth.supabase_client import get_supabase_admin, is_supabase_configured

logger = logging.getLogger("ertmac.alerts.persistence")


def _clean_uuid(val: Optional[str]) -> Optional[str]:
    """Returns val if it is a valid UUID and not dev fallback UUID, else None."""
    if not val:
        return None
    try:
        u = str(uuid.UUID(str(val)))
        if u == "00000000-0000-0000-0000-000000000001":
            return None
        return u
    except (ValueError, TypeError):
        return None


class AlertPersistence:
    """Handles CRUD and state transitions for alerts in Supabase PostgreSQL."""

    @staticmethod
    def create_alert(alert_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Inserts a new alert into Supabase `alerts` table.
        Returns the inserted alert row dict, or None on failure / fallback.
        """
        db = get_supabase_admin()
        if not db:
            return None

        row = {
            "well_id": alert_dict.get("well_id"),
            "organization_id": alert_dict.get("organization_id", "00000000-0000-0000-0000-000000000001"),
            "source": alert_dict.get("source"),
            "severity": alert_dict.get("severity"),
            "status": alert_dict.get("status", "ACTIVE"),
            "title": alert_dict.get("title"),
            "description": alert_dict.get("description"),
            "current_md": alert_dict.get("current_md"),
            "tvd": alert_dict.get("tvd"),
            "evidence": alert_dict.get("evidence"),
            "recommended_action": alert_dict.get("recommended_action"),
            "disclaimer": alert_dict.get("disclaimer", "HISTORICAL OFFSET EVENT — NOT A PREDICTION"),
            "source_record": alert_dict.get("source_record"),
            "deduplication_key": alert_dict.get("deduplication_key"),
            "created_at": alert_dict.get("created_at") or datetime.now(timezone.utc).isoformat(),
            "updated_at": alert_dict.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        }

        try:
            res = db.table("alerts").insert(row).execute()
            if res.data and len(res.data) > 0:
                logger.info(f"[PERSISTENCE] Alert created in DB: {res.data[0]['id']}")
                return res.data[0]
        except Exception as e:
            logger.error(f"[PERSISTENCE] Failed to insert alert into Supabase: {e}")
        return None

    @staticmethod
    def check_deduplication(dedup_key: str) -> bool:
        """Returns True if an active alert with this deduplication_key already exists in DB."""
        if not dedup_key:
            return False
        db = get_supabase_admin()
        if not db:
            return False

        try:
            res = (
                db.table("alerts")
                .select("id")
                .eq("deduplication_key", dedup_key)
                .in_("status", ["ACTIVE", "ACKNOWLEDGED", "INVESTIGATING"])
                .execute()
            )
            return bool(res.data and len(res.data) > 0)
        except Exception as e:
            logger.error(f"[PERSISTENCE] Deduplication check failed: {e}")
            return False

    @staticmethod
    def get_alerts(
        organization_id: str,
        well_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetches alerts from Supabase."""
        db = get_supabase_admin()
        if not db:
            return None

        try:
            query = db.table("alerts").select("*").order("created_at", desc=True).limit(limit)
            query = query.eq("organization_id", organization_id)
            if well_id:
                query = query.eq("well_id", well_id)
            if status:
                query = query.eq("status", status)

            res = query.execute()
            return res.data
        except Exception as e:
            logger.error(f"[PERSISTENCE] Failed to fetch alerts from Supabase: {e}")
            return None

    @staticmethod
    def update_alert_status(
        alert_id: str,
        organization_id: str,
        status: str,
        actor_id: str,
        resolution_summary: Optional[str] = None,
    ) -> bool:
        """Updates alert status and lifecycle actor fields in DB, strictly within the organization."""
        db = get_supabase_admin()
        if not db:
            return False

        now = datetime.now(timezone.utc).isoformat()
        updates: Dict[str, Any] = {
            "status": status,
            "updated_at": now,
        }

        clean_actor = _clean_uuid(actor_id)

        if status == "ACKNOWLEDGED":
            if clean_actor:
                updates["acknowledged_by"] = clean_actor
            updates["acknowledged_at"] = now
        elif status == "INVESTIGATING":
            if clean_actor:
                updates["investigating_by"] = clean_actor
            updates["investigating_at"] = now
        elif status == "RESOLVED":
            if clean_actor:
                updates["resolved_by"] = clean_actor
            updates["resolved_at"] = now
            if resolution_summary:
                updates["resolution_summary"] = resolution_summary

        try:
            res = db.table("alerts").update(updates).eq("id", alert_id).eq("organization_id", organization_id).execute()
            return bool(res.data and len(res.data) > 0)
        except Exception as e:
            logger.error(f"[PERSISTENCE] Failed to update alert {alert_id}: {e}")
            return False

    @staticmethod
    def assign_alert(alert_id: str, organization_id: str, assignee_id: str) -> bool:
        """Assigns an alert to a specific profile UUID, strictly within the organization."""
        db = get_supabase_admin()
        if not db:
            return False

        now = datetime.now(timezone.utc).isoformat()
        clean_assignee = _clean_uuid(assignee_id)

        updates: Dict[str, Any] = {"updated_at": now}
        if clean_assignee:
            updates["assigned_to"] = clean_assignee

        try:
            res = (
                db.table("alerts")
                .update(updates)
                .eq("id", alert_id)
                .eq("organization_id", organization_id)
                .execute()
            )
            return bool(res.data and len(res.data) > 0)
        except Exception as e:
            logger.error(f"[PERSISTENCE] Failed to assign alert {alert_id}: {e}")
            return False

    @staticmethod
    def add_note(alert_id: str, author_id: str, note_text: str, organization_id: str = "00000000-0000-0000-0000-000000000001") -> Optional[Dict[str, Any]]:
        """Inserts a note into `alert_notes` table."""
        db = get_supabase_admin()
        if not db:
            return None

        clean_author = _clean_uuid(author_id)

        row = {
            "alert_id": alert_id,
            "author_id": clean_author,
            "note_text": note_text,
            "organization_id": organization_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            res = db.table("alert_notes").insert(row).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            logger.error(f"[PERSISTENCE] Failed to insert alert note: {e}")
        return None

    @staticmethod
    def get_notes(alert_id: str, organization_id: str) -> List[Dict[str, Any]]:
        """Fetches notes for an alert, verifying organization_id."""
        db = get_supabase_admin()
        if not db:
            return []

        try:
            res = (
                db.table("alert_notes")
                .select("id, alert_id, author_id, note_text, created_at, organization_id")
                .eq("alert_id", alert_id)
                .eq("organization_id", organization_id)
                .order("created_at", desc=False)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"[PERSISTENCE] Failed to fetch notes for alert {alert_id}: {e}")
            return []
