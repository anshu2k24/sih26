"""
PS26121 Phase 3 — Notifications + Escalation Test Suite

Tests verify:
1. User notification preference storage & update (with fallback)
2. In-app notification creation, fetching, and mark-as-read
3. Resend email delivery dispatch audit logging
4. Alert escalation SLA timeout evaluation engine
5. Notification API endpoints (/api/notifications/preferences, feed, mark read, deliveries, escalation)
"""

import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("AUTH_REQUIRED", "false")

from fastapi.testclient import TestClient
from ertmac.api.server import app
from ertmac.notifications.preferences import (
    get_user_preferences,
    update_user_preferences,
)
from ertmac.notifications.delivery import NotificationDeliveryEngine
from ertmac.notifications.escalation import EscalationEngine
from ertmac.alerts.engine import global_alert_engine, AlertSeverity, AlertSource

client = TestClient(app)


class TestNotificationPreferences:
    def test_default_preferences(self):
        user_id = f"test-user-{uuid.uuid4().hex[:6]}"
        prefs = get_user_preferences(user_id)
        assert prefs["email_enabled"] is True
        assert prefs["critical_alerts"] is True
        assert prefs["high_alerts"] is True
        assert prefs["medium_alerts"] is False

    def test_update_preferences(self):
        user_id = f"test-user-{uuid.uuid4().hex[:6]}"
        updated = update_user_preferences(user_id, {"medium_alerts": True, "email_enabled": False})
        assert updated["medium_alerts"] is True
        assert updated["email_enabled"] is False

        fetched = get_user_preferences(user_id)
        assert fetched["medium_alerts"] is True
        assert fetched["email_enabled"] is False


class TestNotificationDeliveryEngine:
    def test_create_and_fetch_in_app_notification(self):
        user_id = f"user-{uuid.uuid4().hex[:6]}"
        title = f"Test Notification {uuid.uuid4().hex[:4]}"
        body = "Test notification body content."

        evt = NotificationDeliveryEngine.create_in_app_notification(
            user_id=user_id,
            title=title,
            body=body,
        )
        assert evt is not None
        assert evt["title"] == title
        assert evt["is_read"] is False

        feed = NotificationDeliveryEngine.get_in_app_notifications(user_id=user_id)
        assert any(e["title"] == title for e in feed)

    def test_mark_as_read(self):
        user_id = f"user-{uuid.uuid4().hex[:6]}"
        evt = NotificationDeliveryEngine.create_in_app_notification(
            user_id=user_id,
            title="Unread Test",
            body="Content",
        )
        notif_id = evt["id"]
        assert evt["is_read"] is False

        ok = NotificationDeliveryEngine.mark_as_read(notif_id)
        assert ok is True

    def test_email_dispatch_logging(self):
        alert_dict = {
            "alert_id": f"ALT_{uuid.uuid4().hex[:8]}",
            "well_id": "15/9-F-14",
            "title": "Loss of Mud Flow",
            "severity": "CRITICAL",
            "current_md": 2100.0,
            "evidence": "Flow meter zero",
            "disclaimer": "HISTORICAL OFFSET EVENT — NOT A PREDICTION",
        }
        deliv = NotificationDeliveryEngine.dispatch_alert_email(
            alert_dict=alert_dict,
            recipient_email="delivered@resend.dev",
        )
        assert deliv is not None
        assert deliv["recipient_email"] == "delivered@resend.dev"
        assert deliv["status"] in ("SENT", "QUEUED", "FAILED")

        history = NotificationDeliveryEngine.get_delivery_history()
        assert len(history) >= 1


class TestEscalationEngine:
    def test_escalation_evaluation(self):
        # Create an unacknowledged alert
        run_id = uuid.uuid4().hex[:6]
        alert = global_alert_engine.create_alert(
            well_id="15/9-F-14",
            title=f"Unacknowledged Kick Warning {run_id}",
            description="Testing SLA escalation",
            severity=AlertSeverity.HIGH,
            source=AlertSource.ML_PREDICTION,
            current_md=2900.0,
            evidence="Flow differential",
            dedup_key=f"escalation-test-{run_id}",
        )
        assert alert is not None

        # Manually backdate created_at to simulate > 30 minutes unacknowledged
        alert.created_at = "2026-08-28T10:00:00Z"

        escalations = EscalationEngine.evaluate_escalations(timeout_minutes=1)
        assert isinstance(escalations, list)


class TestNotificationAPIEndpoints:
    def test_preferences_api(self):
        # GET /api/notifications/preferences
        res_get = client.get("/api/notifications/preferences")
        assert res_get.status_code == 200
        assert "preferences" in res_get.json()

        # PUT /api/notifications/preferences
        res_put = client.put(
            "/api/notifications/preferences",
            json={"medium_alerts": True, "report_notifications": True},
        )
        assert res_put.status_code == 200
        assert res_put.json()["preferences"]["medium_alerts"] is True

    def test_notification_feed_api(self):
        # GET /api/notifications
        res_feed = client.get("/api/notifications")
        assert res_feed.status_code == 200
        data = res_feed.json()
        assert "count" in data
        assert "unread_count" in data
        assert "notifications" in data

    def test_deliveries_api(self):
        # GET /api/notifications/deliveries
        res_deliv = client.get("/api/notifications/deliveries")
        assert res_deliv.status_code == 200
        assert "deliveries" in res_deliv.json()

    def test_escalation_evaluate_api(self):
        # POST /api/notifications/escalate/evaluate
        res_esc = client.post("/api/notifications/escalate/evaluate?timeout_minutes=30")
        assert res_esc.status_code == 200
        assert res_esc.json()["status"] == "success"
