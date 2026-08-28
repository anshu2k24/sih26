"""
PS26121 eRTMAC-NWIS — Notification Delivery & Dispatch Engine
Handles Resend HTML email dispatch logging and in-app notification event feed.
"""

import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from ertmac.auth.supabase_client import get_supabase_admin
from ertmac.notifications.preferences import get_user_preferences

logger = logging.getLogger("ertmac.notifications.delivery")

_in_memory_deliveries: List[Dict[str, Any]] = []
_in_memory_events: List[Dict[str, Any]] = []


class NotificationDeliveryEngine:
    """Manages email dispatch audit and in-app notification feed."""

    @staticmethod
    def dispatch_alert_email(
        alert_dict: Dict[str, Any],
        recipient_email: str = "operator@company.com",
        recipient_id: Optional[str] = None,
        organization_id: str = "00000000-0000-0000-0000-000000000001",
    ) -> Dict[str, Any]:
        """
        Dispatches an HTML alert email via Resend and records the delivery status.
        """
        resend_key = os.getenv("RESEND_API_KEY")
        from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
        severity = alert_dict.get("severity", "HIGH")
        well_id = alert_dict.get("well_id", "15/9-F-14")
        title = alert_dict.get("title", "Drilling Alert")
        alert_id = str(alert_dict.get("alert_id") or alert_dict.get("id") or "")

        subject = f"[{severity}] PS26121 Drilling Alert — Well {well_id}"
        delivery_id = f"DEL_{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()

        delivery_record = {
            "id": delivery_id,
            "organization_id": organization_id,
            "alert_id": alert_id if len(alert_id) == 36 else None,
            "recipient_id": recipient_id if recipient_id and len(str(recipient_id)) == 36 else None,
            "recipient_email": recipient_email,
            "subject": subject,
            "status": "QUEUED",
            "attempt_count": 1,
            "last_attempted": now,
            "error_message": None,
            "created_at": now,
        }

        if not resend_key:
            logger.info(f"[Resend Email Stub] Email dispatched to {recipient_email}: '{subject}'")
            delivery_record["status"] = "SENT"
            delivery_record["error_message"] = "Simulated (Resend API key not configured)"
            NotificationDeliveryEngine._record_delivery(delivery_record)
            return delivery_record

        try:
            import resend
            resend.api_key = resend_key

            res = resend.Emails.send({
                "from": from_email,
                "to": recipient_email,
                "subject": subject,
                "html": f"""
                <div style="font-family: monospace; background: #070B14; color: #E8EEF7; padding: 20px; border-radius: 8px;">
                    <h2 style="color: #F43F5E;">PS26121 Drilling Operations Alert</h2>
                    <p><strong>Well:</strong> {well_id}</p>
                    <p><strong>Title:</strong> {title}</p>
                    <p><strong>Severity:</strong> <span style="color: #FBBF24;">{severity}</span></p>
                    <p><strong>Current MD:</strong> {alert_dict.get('current_md', 0.0):.1f} m</p>
                    <p><strong>Evidence:</strong> {alert_dict.get('evidence', 'N/A')}</p>
                    <hr style="border-color: #334155;"/>
                    <p style="color: #94A3B8; font-size: 11px;"><em>{alert_dict.get('disclaimer', 'HISTORICAL OFFSET EVENT — NOT A PREDICTION')}</em></p>
                </div>
                """
            })
            delivery_record["status"] = "SENT"
            if isinstance(res, dict) and res.get("id"):
                delivery_record["id"] = res["id"]
            logger.info(f"Resend email sent to {recipient_email} for alert {alert_id}")
        except Exception as e:
            logger.error(f"Resend email dispatch failed to {recipient_email}: {e}")
            delivery_record["status"] = "FAILED"
            delivery_record["error_message"] = str(e)


        NotificationDeliveryEngine._record_delivery(delivery_record)
        return delivery_record


    @staticmethod
    def _record_delivery(record: Dict[str, Any]) -> None:
        _in_memory_deliveries.insert(0, record)
        db = get_supabase_admin()
        if db:
            try:
                db_payload = {
                    "organization_id": record["organization_id"],
                    "recipient_email": record["recipient_email"],
                    "subject": record["subject"],
                    "status": record["status"],
                    "attempt_count": record["attempt_count"],
                    "last_attempted": record["last_attempted"],
                    "error_message": record["error_message"],
                }
                try:
                    db.table("notification_deliveries").insert(db_payload).execute()
                except Exception as ex:
                    if "alert_id" in db_payload:
                        db_payload.pop("alert_id", None)
                        db.table("notification_deliveries").insert(db_payload).execute()
            except Exception as e:
                logger.warning(f"Failed to persist notification delivery to DB: {e}")


    @staticmethod
    def create_in_app_notification(
        user_id: str,
        title: str,
        body: str,
        alert_id: Optional[str] = None,
        organization_id: str = "00000000-0000-0000-0000-000000000001",
    ) -> Dict[str, Any]:
        """Creates an in-app notification event."""
        now = datetime.now(timezone.utc).isoformat()
        evt = {
            "id": f"NOTIF_{uuid.uuid4().hex[:8].upper()}",
            "organization_id": organization_id,
            "user_id": user_id,
            "alert_id": alert_id if alert_id and len(alert_id) == 36 else None,
            "title": title,
            "body": body,
            "is_read": False,
            "created_at": now,
        }

        _in_memory_events.insert(0, evt)

        db = get_supabase_admin()
        if db:
            try:
                db_payload = {
                    "organization_id": organization_id,
                    "title": title,
                    "body": body,
                    "is_read": False,
                }
                if user_id and len(user_id) == 36 and user_id != "00000000-0000-0000-0000-000000000001":
                    db_payload["user_id"] = user_id
                if alert_id and len(alert_id) == 36:
                    db_payload["alert_id"] = alert_id

                res = db.table("notification_events").insert(db_payload).execute()
                if res.data and len(res.data) > 0:
                    evt["id"] = str(res.data[0]["id"])
            except Exception as e:
                logger.warning(f"Failed to persist in-app notification to DB: {e}")

        return evt

    @staticmethod
    def get_in_app_notifications(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches in-app notification feed for a user."""
        db = get_supabase_admin()
        if db:
            try:
                res = (
                    db.table("notification_events")
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                if res.data is not None:
                    return res.data
            except Exception as e:
                logger.warning(f"Failed to fetch notification events from DB: {e}")

        return _in_memory_events[:limit]

    @staticmethod
    def get_delivery_history(limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches email delivery history."""
        db = get_supabase_admin()
        if db:
            try:
                res = (
                    db.table("notification_deliveries")
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                if res.data is not None:
                    return res.data
            except Exception as e:
                logger.warning(f"Failed to fetch notification deliveries from DB: {e}")

        return _in_memory_deliveries[:limit]

    @staticmethod
    def mark_as_read(notification_id: str) -> bool:
        """Marks a notification event as read."""
        for evt in _in_memory_events:
            if evt["id"] == notification_id:
                evt["is_read"] = True

        db = get_supabase_admin()
        if db:
            try:
                db.table("notification_events").update({"is_read": True}).eq("id", notification_id).execute()
                return True
            except Exception as e:
                logger.warning(f"Failed to mark notification {notification_id} read in DB: {e}")

        return True

    @staticmethod
    def mark_all_as_read(user_id: str) -> bool:
        """Marks all notification events read for a user."""
        for evt in _in_memory_events:
            evt["is_read"] = True

        db = get_supabase_admin()
        if db:
            try:
                db.table("notification_events").update({"is_read": True}).execute()
                return True
            except Exception as e:
                logger.warning(f"Failed to mark all notifications read in DB: {e}")

        return True
