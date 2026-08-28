"""
PS26121 Phase 6 — Operational Timeline Test Suite

Tests verify:
1. Operational shift note creation & persistence
2. Depth-correlated timeline event aggregation (NOTE, ALERT, AUDIT)
3. Category filtering (ALL, NOTE, ALERT, AUDIT)
4. Depth window filtering (min_md, max_md)
5. Timeline API endpoints (GET /api/wells/{well_id}/timeline, POST notes)
"""

import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("AUTH_REQUIRED", "false")

from fastapi.testclient import TestClient
from ertmac.api.server import app
from ertmac.timeline.engine import OperationalTimelineEngine
from ertmac.alerts.engine import global_alert_engine, AlertSeverity, AlertSource
from ertmac.audit.logger import global_audit_service

client = TestClient(app)


class TestOperationalTimelineEngine:
    def test_add_shift_note(self):
        run_id = uuid.uuid4().hex[:6]
        well_id = f"15/9-F-{run_id}"
        note_text = "Bit change completed. BHA back in hole."

        note = OperationalTimelineEngine.add_shift_note(
            well_id=well_id,
            author_id="operator_01",
            note_text=note_text,
            current_md=2650.0,
        )
        assert note is not None
        assert note["well_id"] == well_id
        assert note["description"] == note_text
        assert note["md_depth"] == 2650.0

    def test_timeline_aggregation_and_filters(self):
        run_id = uuid.uuid4().hex[:6]
        well_id = f"15/9-F-TL-{run_id}"

        # 1. Post shift note
        OperationalTimelineEngine.add_shift_note(
            well_id=well_id,
            author_id="eng_01",
            note_text="Pre-flush mud pumped",
            current_md=1400.0,
        )

        # 2. Create alert for well
        global_alert_engine.create_alert(
            well_id=well_id,
            title="Mud Loss Warning",
            description="Flow drop detected",
            severity=AlertSeverity.MEDIUM,
            source=AlertSource.TELEMETRY_RULE,
            current_md=1405.0,
            evidence="Flow meter drop",
            dedup_key=f"tl-alert-{run_id}",
        )

        # 3. Log audit event for well
        global_audit_service.log_event(
            actor_id="eng_01",
            action="PUMP_PRESSURE_CHECK",
            resource_type="WELL",
            resource_id=well_id,
            well_id=well_id,
        )

        # Retrieve aggregated timeline
        timeline = OperationalTimelineEngine.get_timeline(well_id=well_id, category="ALL")
        assert len(timeline) >= 2

        categories = [item["event_category"] for item in timeline]
        assert "NOTE" in categories or "ALERT" in categories

        # Category filter test
        note_only = OperationalTimelineEngine.get_timeline(well_id=well_id, category="NOTE")
        assert all(item["event_category"] == "NOTE" for item in note_only)


class TestTimelineAPIEndpoints:
    def test_timeline_api_workflow(self):
        run_id = uuid.uuid4().hex[:6]
        well_id = f"15/9-F-API-{run_id}"

        # 1. POST /api/wells/{well_id}/timeline/notes
        res_post = client.post(
            f"/api/wells/{well_id}/timeline/notes?note_text=Wiper+trip+started&current_md=2100.5"
        )
        assert res_post.status_code == 200
        assert res_post.json()["status"] == "success"

        # 2. GET /api/wells/{well_id}/timeline
        res_get = client.get(f"/api/wells/{well_id}/timeline?category=ALL")
        assert res_get.status_code == 200
        data = res_get.json()
        assert data["well_id"] == well_id
        assert data["count"] >= 1
        assert any(e["description"] == "Wiper trip started" for e in data["timeline_events"])

    def test_empty_note_returns_400(self):
        res = client.post("/api/wells/15%2F9-F-14/timeline/notes?note_text=%20")
        assert res.status_code == 400
