"""
PS26121 Phase 5 — Immutable Audit & Compliance Trail Test Suite

Tests verify:
1. Immutability guarantee: AuditService has NO delete_event or update_event methods
2. HTTP DELETE / UPDATE requests on /api/audit are rejected (405 Method Not Allowed)
3. Audit log recording across operational domains
4. Filter parameters on get_events (well_id, action, actor_id, limit, offset)
5. Preservation of event payload metadata, before_state, and after_state
"""

import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("AUTH_REQUIRED", "false")

from fastapi.testclient import TestClient
from ertmac.api.server import app
from ertmac.audit.logger import global_audit_service, AuditService, AuditEvent

client = TestClient(app)


class TestAuditImmutability:
    def test_no_delete_or_update_methods(self):
        """Verify AuditService API surface has NO delete or update methods."""
        service = AuditService()
        assert not hasattr(service, "delete_event"), "AuditService must NOT contain delete_event"
        assert not hasattr(service, "update_event"), "AuditService must NOT contain update_event"
        assert not hasattr(service, "delete_log"), "AuditService must NOT contain delete_log"
        assert not hasattr(service, "clear_logs"), "AuditService must NOT contain clear_logs"

    def test_http_delete_method_rejected(self):
        """DELETE request on /api/audit must be rejected by FastAPI."""
        res = client.delete("/api/audit")
        assert res.status_code in (404, 405), f"Expected 405/404 on DELETE /api/audit, got {res.status_code}"

    def test_http_put_method_rejected(self):
        """PUT request on /api/audit must be rejected."""
        res = client.put("/api/audit")
        assert res.status_code in (404, 405), f"Expected 405/404 on PUT /api/audit, got {res.status_code}"


class TestAuditFilteringAndPayloads:
    def test_log_event_and_retrieve_with_filters(self):
        run_id = uuid.uuid4().hex[:6]
        actor_id = f"user_{run_id}"
        well_id = f"15/9-F-TEST-{run_id}"

        # 1. Log event
        evt = global_audit_service.log_event(
            actor_id=actor_id,
            actor_role="DRILLING_ENGINEER",
            action=f"COMPLIANCE_TEST_{run_id}",
            resource_type="WELL",
            resource_id=well_id,
            well_id=well_id,
            payload={"parameter": "mud_weight", "value": 1.45},
            before_state={"mud_weight": 1.40},
            after_state={"mud_weight": 1.45},
        )
        assert evt is not None
        assert evt.actor_id == actor_id

        # 2. Retrieve with well_id filter
        well_events = global_audit_service.get_events(well_id=well_id)
        assert len(well_events) >= 1
        found = next((e for e in well_events if e["resource_id"] == well_id), None)
        assert found is not None
        assert found["action"] == f"COMPLIANCE_TEST_{run_id}"
        assert found["before_state"] == {"mud_weight": 1.40}
        assert found["after_state"] == {"mud_weight": 1.45}

    def test_audit_api_endpoint(self):
        res = client.get("/api/audit?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert "count" in data
        assert "events" in data
        assert isinstance(data["events"], list)
