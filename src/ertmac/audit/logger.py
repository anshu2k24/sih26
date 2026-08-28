"""
PS26121 eRTMAC-NWIS — Operational Audit Trail System
Append-only audit logger. Persists to Supabase when configured,
falls back to in-memory ring buffer when database unavailable.

IMMUTABILITY GUARANTEE:
- No UPDATE operations exist on audit records.
- No DELETE operations exist on audit records.
- In-memory buffer is append-only (oldest evicted only when cap exceeded).
- Supabase RLS blocks UPDATE and DELETE at database level.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger("AuditLogger")


class AuditEvent:
    def __init__(
        self,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        actor_role: Optional[str] = None,
        well_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
    ):
        self.audit_id = f"AUD_{uuid.uuid4().hex[:8].upper()}"
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.well_id = well_id
        self.organization_id = organization_id or "00000000-0000-0000-0000-000000000001"
        self.payload = payload or {}
        self.request_id = request_id
        self.ip_address = ip_address
        self.before_state = before_state
        self.after_state = after_state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "well_id": self.well_id,
            "organization_id": self.organization_id,
            "payload": self.payload,
            "request_id": self.request_id,
            "ip_address": self.ip_address,
            "before_state": self.before_state,
            "after_state": self.after_state,
        }

    def to_db_dict(self) -> Dict[str, Any]:
        """Returns a dict suitable for Supabase insert (column names match schema)."""
        valid_actor_uuid = None
        if self.actor_id:
            try:
                uuid.UUID(str(self.actor_id))
                # Exclude dev-user fallback uuid if it's not registered in auth.users
                if self.actor_id != "00000000-0000-0000-0000-000000000001":
                    valid_actor_uuid = self.actor_id
            except (ValueError, TypeError):
                valid_actor_uuid = None

        meta = self.payload or {}
        if not valid_actor_uuid and self.actor_id:
            meta["actor_id_raw"] = self.actor_id

        return {
            "actor_user_id": valid_actor_uuid,
            "actor_role": self.actor_role,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "well_id": self.well_id,
            "organization_id": self.organization_id,
            "metadata": meta,
            "request_id": self.request_id,
            "before_state": self.before_state,
            "after_state": self.after_state,
        }


class AuditService:
    def __init__(self, max_in_memory: int = 1000):
        self.max_in_memory = max_in_memory
        self._events: List[AuditEvent] = []

    def log_event(
        self,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        actor_role: Optional[str] = None,
        well_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        evt = AuditEvent(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_role=actor_role,
            well_id=well_id,
            organization_id=organization_id,
            payload=payload,
            request_id=request_id,
            ip_address=ip_address,
            before_state=before_state,
            after_state=after_state,
        )

        # Always append to in-memory buffer
        self._events.append(evt)
        if len(self._events) > self.max_in_memory:
            self._events.pop(0)

        logger.info(
            f"[AUDIT] {actor_role or 'UNKNOWN'} '{actor_id}' → '{action}' "
            f"on {resource_type}:{resource_id}"
        )

        # Attempt Supabase persistence
        self._persist_to_db(evt)

        return evt

    def _persist_to_db(self, evt: AuditEvent) -> None:
        """
        Attempts to persist audit event to Supabase audit_logs table.
        Silently logs error on failure — never crashes the calling operation.
        """
        try:
            from ertmac.auth.supabase_client import get_supabase_admin
            db = get_supabase_admin()
            if not db:
                return  # Supabase not configured — in-memory only

            db.table("audit_logs").insert(evt.to_db_dict()).execute()
        except Exception as e:
            logger.warning(f"[AUDIT] Supabase persistence failed (in-memory fallback): {e}")

    def get_events(
        self,
        well_id: Optional[str] = None,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves audit events. Tries Supabase first, falls back to in-memory.
        """
        # Try Supabase first for persistent results
        try:
            from ertmac.auth.supabase_client import get_supabase_admin
            db = get_supabase_admin()
            if db:
                return self._get_from_db(
                    db=db,
                    well_id=well_id,
                    action=action,
                    actor_id=actor_id,
                    organization_id=organization_id,
                    limit=limit,
                    offset=offset,
                )
        except Exception as e:
            logger.warning(f"[AUDIT] DB read failed, using in-memory: {e}")

        # In-memory fallback
        filtered = self._events
        if well_id:
            filtered = [e for e in filtered if e.well_id == well_id]
        if action:
            filtered = [e for e in filtered if e.action == action]
        if actor_id:
            filtered = [e for e in filtered if e.actor_id == actor_id]
        if organization_id:
            filtered = [e for e in filtered if e.organization_id == organization_id]

        paginated = list(reversed(filtered))
        if offset:
            paginated = paginated[offset:]
        paginated = paginated[:limit]
        return [e.to_dict() for e in paginated]

    def _get_from_db(
        self,
        db,
        well_id: Optional[str],
        action: Optional[str],
        actor_id: Optional[str],
        organization_id: Optional[str],
        limit: int,
        offset: int,
    ) -> List[Dict[str, Any]]:
        """Fetches audit logs from Supabase with filters."""
        query = (
            db.table("audit_logs")
            .select(
                "id, actor_user_id, actor_role, action, resource_type, "
                "resource_id, well_id, organization_id, metadata, "
                "before_state, after_state, created_at"
            )
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )

        if well_id:
            query = query.eq("well_id", well_id)
        if action:
            query = query.eq("action", action)
        if actor_id:
            query = query.eq("actor_user_id", actor_id)
        if organization_id:
            query = query.eq("organization_id", organization_id)

        result = query.execute()
        rows = result.data or []

        # Map DB column names back to API response format
        return [
            {
                "audit_id": r.get("id"),
                "timestamp": r.get("created_at"),
                "actor_id": r.get("actor_user_id") or (r.get("metadata") or {}).get("actor_id_raw", "SYSTEM"),
                "actor_role": r.get("actor_role"),
                "action": r.get("action"),
                "resource_type": r.get("resource_type"),
                "resource_id": r.get("resource_id"),
                "well_id": r.get("well_id"),
                "organization_id": r.get("organization_id"),
                "payload": r.get("metadata", {}),
                "before_state": r.get("before_state"),
                "after_state": r.get("after_state"),
            }
            for r in rows
        ]


# Global singleton
global_audit_service = AuditService()
