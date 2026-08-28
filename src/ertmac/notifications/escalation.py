"""
PS26121 eRTMAC-NWIS — Alert Escalation Engine
Checks unacknowledged active alerts against SLA timeout rules and escalates to superintendents.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from ertmac.alerts.engine import global_alert_engine, AlertStatus, AlertSeverity
from ertmac.notifications.delivery import NotificationDeliveryEngine

logger = logging.getLogger("ertmac.notifications.escalation")


class EscalationEngine:
    """Evaluates SLA timeouts on active alerts and executes escalation policies."""

    @staticmethod
    def evaluate_escalations(timeout_minutes: int = 30) -> List[Dict[str, Any]]:
        """
        Scans active alerts. If an alert has been ACTIVE without acknowledgment
        for longer than timeout_minutes, triggers an escalation dispatch.
        """
        escalated: List[Dict[str, Any]] = []
        active_alerts = global_alert_engine.get_active_alerts()

        now = datetime.now(timezone.utc)

        for alt in active_alerts:
            if alt.get("status") != "ACTIVE":
                continue

            created_str = alt.get("created_at")
            if not created_str:
                continue

            try:
                # Handle Z or +00:00 ISO strings
                created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                elapsed_min = (now - created_dt).total_seconds() / 60.0

                if elapsed_min >= timeout_minutes:
                    # Escalation triggered
                    well_id = alt.get("well_id", "Unknown")
                    title = alt.get("title", "Drilling Alert")
                    alert_id = alt.get("alert_id")

                    logger.warning(
                        f"[ESCALATION] Alert {alert_id} on well {well_id} unacknowledged for {elapsed_min:.1f} mins. Escalating!"
                    )

                    # 1. Create in-app escalation event
                    evt = NotificationDeliveryEngine.create_in_app_notification(
                        user_id=alt.get("assigned_to") or "00000000-0000-0000-0000-000000000001",
                        title=f"ESCALATION: Unacknowledged Alert ({well_id})",
                        body=f"Alert '{title}' has been unacknowledged for {elapsed_min:.0f} minutes. Immediate superintendent review required.",
                        alert_id=alert_id if len(str(alert_id)) == 36 else None,
                    )

                    # 2. Dispatch escalation email
                    alt_copy = alt.copy()
                    alt_copy["severity"] = "CRITICAL"
                    alt_copy["title"] = f"ESCALATED: {title}"
                    delivery = NotificationDeliveryEngine.dispatch_alert_email(
                        alert_dict=alt_copy,
                        recipient_email="drilling.superintendent@equinor-volve.com",
                    )

                    escalated.append({
                        "alert_id": alert_id,
                        "well_id": well_id,
                        "elapsed_minutes": round(elapsed_min, 1),
                        "notification_event_id": evt.get("id"),
                        "delivery_id": delivery.get("id"),
                    })
            except Exception as e:
                logger.error(f"Error evaluating escalation for alert {alt.get('alert_id')}: {e}")

        return escalated
