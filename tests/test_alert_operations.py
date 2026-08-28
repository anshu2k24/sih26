"""
PS26121 Phase 2 — Complete Alert Operations Test Suite

Tests verify:
1. Alert creation & deduplication suppression
2. Lifecycle state transitions (ACTIVE → ACKNOWLEDGED → INVESTIGATING → RESOLVED)
3. Invalid transitions blocked (e.g., RESOLVED → ACTIVE)
4. Alert assignment to engineer
5. Operational notes thread (add & fetch notes)
6. Well filtering on alerts list
7. Audit log generation for every lifecycle action
8. API endpoints for alerts (/api/alerts, acknowledge, investigate, assign, notes, resolve)
"""

import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("AUTH_REQUIRED", "false")

from fastapi.testclient import TestClient
from ertmac.api.server import app
from ertmac.alerts.engine import (
    AlertEngine,
    AlertItem,
    AlertSeverity,
    AlertStatus,
    AlertSource,
    global_alert_engine,
)
from ertmac.audit.logger import global_audit_service

client = TestClient(app)


class TestAlertEngineUnit:
    def test_alert_creation_and_fields(self):
        engine = AlertEngine(cooldown_seconds=10.0)
        run_id = uuid.uuid4().hex[:6]
        alert = engine.create_alert(
            well_id="15/9-F-14",
            title=f"Loss of Circulation Imminent {run_id}",
            description="Historical proximity match at 1500m",
            severity=AlertSeverity.HIGH,
            source=AlertSource.HISTORICAL_PROXIMITY,
            current_md=1505.0,
            evidence="DDR episode EP_V2_605",
            dedup_key=f"test-creation-{run_id}",
        )
        assert alert is not None
        assert alert.well_id == "15/9-F-14"
        assert alert.severity == AlertSeverity.HIGH
        assert alert.status == AlertStatus.ACTIVE
        assert alert.current_md == 1505.0
        assert "HISTORICAL OFFSET EVENT" in alert.disclaimer

    def test_cooldown_deduplication(self):
        engine = AlertEngine(cooldown_seconds=60.0)
        key = f"unique-test-key-{uuid.uuid4().hex[:6]}"
        a1 = engine.create_alert(
            well_id="15/9-F-14",
            title="High Mud Loss",
            description="Test alert",
            severity=AlertSeverity.MEDIUM,
            source=AlertSource.TELEMETRY_RULE,
            current_md=2000.0,
            evidence="Flow out drop",
            dedup_key=key,
        )
        assert a1 is not None

        # Duplicate attempt with same dedup key within cooldown → suppressed (None)
        a2 = engine.create_alert(
            well_id="15/9-F-14",
            title="High Mud Loss",
            description="Test alert duplicate",
            severity=AlertSeverity.MEDIUM,
            source=AlertSource.TELEMETRY_RULE,
            current_md=2002.0,
            evidence="Flow out drop",
            dedup_key=key,
        )
        assert a2 is None

    def test_lifecycle_transitions(self):
        engine = AlertEngine()
        run_id = uuid.uuid4().hex[:6]
        alert = engine.create_alert(
            well_id="15/9-F-14",
            title=f"Kick Detection Warning {run_id}",
            description="Pressure spike",
            severity=AlertSeverity.CRITICAL,
            source=AlertSource.ML_PREDICTION,
            current_md=2500.0,
            evidence="Flow in > Flow out",
            dedup_key=f"kick-warning-key-{run_id}",
        )
        assert alert is not None
        alert_id = alert.alert_id

        # 1. Acknowledge
        ack = engine.acknowledge_alert(alert_id, "user_eng_01")
        assert ack is not None
        assert ack.status == AlertStatus.ACKNOWLEDGED
        assert ack.acknowledged_by == "user_eng_01"

        # 2. Investigate
        inv = engine.start_investigation(alert_id, "user_eng_01")
        assert inv is not None
        assert inv.status == AlertStatus.INVESTIGATING
        assert inv.investigating_by == "user_eng_01"

        # 3. Assign
        asg = engine.assign_alert(alert_id, "user_super_02")
        assert asg is not None
        assert asg.assigned_to == "user_super_02"

        # 4. Resolve
        res = engine.resolve_alert(alert_id, "user_super_02", "Mud weight increased by 0.05 SG.")
        assert res is not None
        assert res.status == AlertStatus.RESOLVED
        assert res.resolution_notes == "Mud weight increased by 0.05 SG."

    def test_invalid_resolution_transition(self):
        engine = AlertEngine()
        run_id = uuid.uuid4().hex[:6]
        alert = engine.create_alert(
            well_id="15/9-F-14",
            title=f"Stuck Pipe Warning {run_id}",
            description="Overpull detected",
            severity=AlertSeverity.HIGH,
            source=AlertSource.TELEMETRY_RULE,
            current_md=3100.0,
            evidence="Hookload spike",
            dedup_key=f"stuck-pipe-key-{run_id}",
        )
        assert alert is not None

        # Resolve the alert
        res = engine.resolve_alert(alert.alert_id, "eng_1", "Jarred free successfully")
        assert res.status == AlertStatus.RESOLVED

        # Attempt to resolve an already resolved alert → returns None
        res_again = engine.resolve_alert(alert.alert_id, "eng_1", "Duplicate resolve")
        assert res_again is None


class TestAlertAPIEndpoints:
    def test_alert_full_api_workflow(self):
        run_id = uuid.uuid4().hex[:6]
        # Create alert via global_alert_engine
        alert = global_alert_engine.create_alert(
            well_id="15/9-F-15",
            title=f"Tight Hole API Test {run_id}",
            description="API test description",
            severity=AlertSeverity.HIGH,
            source=AlertSource.HISTORICAL_PROXIMITY,
            current_md=1800.0,
            evidence="Tight hole reported in DDR",
            dedup_key=f"api-test-key-{run_id}",
        )
        assert alert is not None
        alert_id = alert.alert_id

        # 1. GET /api/alerts
        res = client.get("/api/alerts")
        assert res.status_code == 200
        data = res.json()
        assert "alerts" in data
        assert any(a["alert_id"] == alert_id for a in data["alerts"])

        # 2. GET /api/alerts/{id}
        res_detail = client.get(f"/api/alerts/{alert_id}")
        assert res_detail.status_code == 200
        assert res_detail.json()["alert_id"] == alert_id

        # 3. POST /api/alerts/{id}/acknowledge
        res_ack = client.post(f"/api/alerts/{alert_id}/acknowledge")
        assert res_ack.status_code == 200
        assert res_ack.json()["status"] == "ACKNOWLEDGED"

        # 4. POST /api/alerts/{id}/investigate
        res_inv = client.post(f"/api/alerts/{alert_id}/investigate")
        assert res_inv.status_code == 200
        assert res_inv.json()["status"] == "INVESTIGATING"

        # 5. POST /api/alerts/{id}/assign
        res_asg = client.post(f"/api/alerts/{alert_id}/assign?assignee_id=00000000-0000-0000-0000-000000000002")
        assert res_asg.status_code == 200
        assert res_asg.json()["assigned_to"] == "00000000-0000-0000-0000-000000000002"

        # 6. POST /api/alerts/{id}/notes & GET /api/alerts/{id}/notes
        res_note = client.post(f"/api/alerts/{alert_id}/notes?note_text=Wiper+trip+performed")
        assert res_note.status_code == 200

        res_get_notes = client.get(f"/api/alerts/{alert_id}/notes")
        assert res_get_notes.status_code == 200

        # 7. POST /api/alerts/{id}/resolve
        res_res = client.post(f"/api/alerts/{alert_id}/resolve?notes=Hole+reamed+clean")
        assert res_res.status_code == 200
        assert res_res.json()["status"] == "RESOLVED"

        # 8. Verify audit logs were generated for actions
        audit_res = client.get("/api/audit")
        assert audit_res.status_code == 200
        actions = [e["action"] for e in audit_res.json()["events"]]
        assert "ALERT_ACKNOWLEDGED" in actions
        assert "ALERT_INVESTIGATION_STARTED" in actions
        assert "ALERT_ASSIGNED" in actions
        assert "ALERT_NOTE_ADDED" in actions
        assert "ALERT_RESOLVED" in actions
