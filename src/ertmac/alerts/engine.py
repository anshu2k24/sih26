"""
PS26121 eRTMAC-NWIS — Production Alert & Notification Engine
Manages alert lifecycles, severity classification, deduplication windows, real-time dispatch, and Resend email integration.
Supports dual operational mode: Supabase DB persistence when configured, in-memory fallback when offline.
"""

import os
import time
import uuid
import logging
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from ertmac.alerts.persistence import AlertPersistence

logger = logging.getLogger("AlertEngine")


class AlertSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class AlertSource(str, Enum):
    HISTORICAL_PROXIMITY = "HISTORICAL_PROXIMITY"
    ML_PREDICTION = "ML_PREDICTION"
    TELEMETRY_RULE = "TELEMETRY_RULE"
    DATA_QUALITY = "DATA_QUALITY"
    SYSTEM = "SYSTEM"


class AlertItem:
    def __init__(
        self,
        well_id: str,
        title: str,
        description: str,
        severity: AlertSeverity,
        source: AlertSource,
        current_md: float,
        evidence: str,
        source_record: Optional[str] = None,
        disclaimer: str = "HISTORICAL OFFSET EVENT — NOT A PREDICTION",
        alert_id: Optional[str] = None,
        organization_id: str = "00000000-0000-0000-0000-000000000001",
    ):
        self.alert_id = alert_id or f"ALT_{uuid.uuid4().hex[:8].upper()}"
        self.well_id = well_id
        self.title = title
        self.description = description
        self.severity = severity if isinstance(severity, AlertSeverity) else AlertSeverity(severity)
        self.source = source if isinstance(source, AlertSource) else AlertSource(source)
        self.current_md = current_md
        self.evidence = evidence
        self.source_record = source_record
        self.disclaimer = disclaimer
        self.status = AlertStatus.ACTIVE
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at
        self.acknowledged_by: Optional[str] = None
        self.acknowledged_at: Optional[str] = None
        self.investigating_by: Optional[str] = None
        self.investigating_at: Optional[str] = None
        self.assigned_to: Optional[str] = None
        self.resolved_by: Optional[str] = None
        self.resolved_at: Optional[str] = None
        self.organization_id = organization_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "well_id": self.well_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value if isinstance(self.severity, AlertSeverity) else self.severity,
            "source": self.source.value if isinstance(self.source, AlertSource) else self.source,
            "current_md": self.current_md,
            "evidence": self.evidence,
            "source_record": self.source_record,
            "disclaimer": self.disclaimer,
            "status": self.status.value if isinstance(self.status, AlertStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at,
            "investigating_by": self.investigating_by,
            "investigating_at": self.investigating_at,
            "assigned_to": self.assigned_to,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at,
            "resolution_notes": self.resolution_notes,
            "organization_id": self.organization_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AlertItem":
        item = cls(
            well_id=d.get("well_id", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            severity=d.get("severity", AlertSeverity.INFO),
            source=d.get("source", AlertSource.SYSTEM),
            current_md=d.get("current_md", 0.0),
            evidence=d.get("evidence", ""),
            source_record=d.get("source_record"),
            disclaimer=d.get("disclaimer", "HISTORICAL OFFSET EVENT — NOT A PREDICTION"),
            alert_id=str(d.get("id") or d.get("alert_id")),
            organization_id=d.get("organization_id", "00000000-0000-0000-0000-000000000001"),
        )
        item.status = AlertStatus(d.get("status", "ACTIVE"))
        item.created_at = d.get("created_at") or item.created_at
        item.updated_at = d.get("updated_at") or item.updated_at
        item.acknowledged_by = d.get("acknowledged_by")
        item.acknowledged_at = d.get("acknowledged_at")
        item.investigating_by = d.get("investigating_by")
        item.investigating_at = d.get("investigating_at")
        item.assigned_to = d.get("assigned_to")
        item.resolved_by = d.get("resolved_by")
        item.resolved_at = d.get("resolved_at")
        item.resolution_notes = d.get("resolution_summary") or d.get("resolution_notes")
        return item


class AlertEngine:
    def __init__(self, cooldown_seconds: float = 60.0):
        self.cooldown_seconds = cooldown_seconds
        self._alerts: Dict[str, AlertItem] = {}
        self._last_trigger_times: Dict[str, float] = {}

    def create_alert(
        self,
        well_id: str,
        title: str,
        description: str,
        severity: AlertSeverity,
        source: AlertSource,
        current_md: float,
        evidence: str,
        organization_id: str,
        source_record: Optional[str] = None,
        dedup_key: Optional[str] = None
    ) -> Optional[AlertItem]:
        now = time.time()
        key = dedup_key or f"{well_id}:{source.value if isinstance(source, AlertSource) else source}:{title}:{round(current_md / 10.0)}"

        # Cooldown check in memory
        if key in self._last_trigger_times:
            if now - self._last_trigger_times[key] < self.cooldown_seconds:
                return None  # Cooldown active, suppress duplicate alert

        # Cooldown check in DB if available
        if AlertPersistence.check_deduplication(key):
            return None

        self._last_trigger_times[key] = now
        alert = AlertItem(
            well_id=well_id,
            title=title,
            description=description,
            severity=severity,
            source=source,
            current_md=current_md,
            evidence=evidence,
            source_record=source_record,
            organization_id=organization_id
        )

        self._alerts[alert.alert_id] = alert

        # DB persistence
        db_alert = alert.to_dict()
        db_alert["deduplication_key"] = key
        inserted_row = AlertPersistence.create_alert(db_alert)
        if inserted_row:
            db_id = str(inserted_row["id"])
            # Update memory dict key to match DB UUID
            del self._alerts[alert.alert_id]
            alert.alert_id = db_id
            self._alerts[db_id] = alert

        # Always create in-app notification event for new alerts
        try:
            from ertmac.notifications.delivery import NotificationDeliveryEngine
            NotificationDeliveryEngine.create_in_app_notification(
                user_id="00000000-0000-0000-0000-000000000001",
                organization_id=organization_id,
                title=f"[{alert.severity.value if isinstance(alert.severity, AlertSeverity) else alert.severity}] {alert.title}",
                body=f"Well {well_id} @ {current_md:.1f}m: {evidence}",
                alert_id=alert.alert_id if len(alert.alert_id) == 36 else None,
            )
        except Exception as e:
            logger.warning(f"Failed to create in-app notification event: {e}")

        # Dispatch email if HIGH or CRITICAL
        if severity in (AlertSeverity.HIGH, AlertSeverity.CRITICAL):
            self._dispatch_email_notification(alert)

        return alert

    def _dispatch_email_notification(self, alert: AlertItem) -> bool:
        try:
            from ertmac.notifications.delivery import NotificationDeliveryEngine
            from ertmac.config.settings import get_notification_recipient_email
            target_email = get_notification_recipient_email()
            NotificationDeliveryEngine.dispatch_alert_email(alert.to_dict(), recipient_email=target_email)
            return True
        except Exception as e:
            logger.error(f"Failed to dispatch alert email: {e}")
            return False



    def start_investigation(self, alert_id: str, user_id: str, organization_id: str) -> Optional[AlertItem]:
        alert = self._get_alert_item(alert_id, organization_id)
        if not alert:
            return None
        # Valid: ACTIVE or ACKNOWLEDGED → INVESTIGATING
        if alert.status not in (AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED):
            return None

        alert.status = AlertStatus.INVESTIGATING
        alert.investigating_by = user_id
        alert.investigating_at = datetime.now(timezone.utc).isoformat()
        alert.updated_at = alert.investigating_at
        self._alerts[alert.alert_id] = alert

        AlertPersistence.update_alert_status(alert.alert_id, organization_id, "INVESTIGATING", user_id)
        return alert

    def acknowledge_alert(self, alert_id: str, user_id: str, organization_id: str) -> Optional[AlertItem]:
        alert = self._get_alert_item(alert_id, organization_id)
        if not alert:
            return None
        # Valid: ACTIVE → ACKNOWLEDGED
        if alert.status != AlertStatus.ACTIVE:
            return None

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.now(timezone.utc).isoformat()
        alert.updated_at = alert.acknowledged_at
        self._alerts[alert.alert_id] = alert

        AlertPersistence.update_alert_status(alert.alert_id, organization_id, "ACKNOWLEDGED", user_id)
        return alert

    def resolve_alert(self, alert_id: str, user_id: str, notes: str, organization_id: str) -> Optional[AlertItem]:
        alert = self._get_alert_item(alert_id, organization_id)
        if not alert:
            return None
        # Block invalid transition RESOLVED -> ACTIVE or RESOLVED -> RESOLVED
        if alert.status == AlertStatus.RESOLVED:
            return None

        alert.status = AlertStatus.RESOLVED
        alert.resolved_by = user_id
        alert.resolved_at = datetime.now(timezone.utc).isoformat()
        alert.resolution_notes = notes
        alert.updated_at = alert.resolved_at
        self._alerts[alert.alert_id] = alert

        AlertPersistence.update_alert_status(alert.alert_id, organization_id, "RESOLVED", user_id, resolution_summary=notes)
        return alert

    def assign_alert(self, alert_id: str, assignee_id: str, organization_id: str) -> Optional[AlertItem]:
        alert = self._get_alert_item(alert_id, organization_id)
        if not alert:
            return None
        alert.assigned_to = assignee_id
        alert.updated_at = datetime.now(timezone.utc).isoformat()
        self._alerts[alert.alert_id] = alert

        AlertPersistence.assign_alert(alert.alert_id, organization_id, assignee_id)
        return alert

    def add_note(self, alert_id: str, author_id: str, note_text: str) -> Optional[Dict[str, Any]]:
        return AlertPersistence.add_note(alert_id, author_id, note_text)

    def get_notes(self, alert_id: str, organization_id: str) -> List[Dict[str, Any]]:
        return AlertPersistence.get_notes(alert_id, organization_id)

    def _get_alert_item(self, alert_id: str, organization_id: str) -> Optional[AlertItem]:
        if alert_id in self._alerts:
            alt = self._alerts[alert_id]
            if alt.organization_id == organization_id:
                return alt
            return None
        
        # Check DB
        db_alerts = AlertPersistence.get_alerts(organization_id=organization_id, limit=500)
        if db_alerts:
            for row in db_alerts:
                if str(row.get("id")) == alert_id or str(row.get("alert_id")) == alert_id:
                    item = AlertItem.from_dict(row)
                    self._alerts[item.alert_id] = item
                    return item
        return None

    def get_active_alerts(self, organization_id: str, well_id: Optional[str] = None) -> List[Dict[str, Any]]:
        # Try DB first
        db_alerts = AlertPersistence.get_alerts(organization_id=organization_id, well_id=well_id, limit=200)
        if db_alerts is not None:
            # Sync to in-memory cache
            res = []
            for row in db_alerts:
                item = AlertItem.from_dict(row)
                self._alerts[item.alert_id] = item
                res.append(item.to_dict())
            return res

        # In-memory fallback
        res = []
        for alt in self._alerts.values():
            if alt.organization_id != organization_id:
                continue
            if well_id and alt.well_id != well_id:
                continue
            res.append(alt.to_dict())
        res.sort(key=lambda x: x["created_at"], reverse=True)
        return res


# Global instance
global_alert_engine = AlertEngine()
