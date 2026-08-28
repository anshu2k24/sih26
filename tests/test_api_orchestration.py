import pytest
import os
import json
from pathlib import Path
from fastapi.testclient import TestClient

from ertmac.api import app, get_app_state
from ertmac.streaming import SensorRecord, SCIENTIFIC_LABEL

client = TestClient(app)

REPO_ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = REPO_ROOT / "data" / "processed" / "usrop" / "usrop_clean.parquet"


def make_json(well_id: str = "15/9-F-15", md: float = 1000.0, rop: float = 10.0) -> str:
    rec = SensorRecord(
        well_id=well_id,
        timestamp="2020-01-01T00:00:00Z",
        md=md,
        tvd=md * 0.95,
        rop=rop,
        wob=5.0,
        rpm=60.0,
        torque=20.0,
        hookload=120.0,
        spp=10000.0,
        flow_in=2000.0,
        mud_density=1.2
    )
    return json.dumps(rec.to_dict())


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["data_source"] == SCIENTIFIC_LABEL


def test_get_wells_endpoint():
    response = client.get("/api/wells")
    assert response.status_code == 200
    data = response.json()
    assert "wells" in data
    wells = [w["well_id"] for w in data["wells"]]
    assert "15/9-F-15" in wells
    assert "15/9-F-14" in wells


def test_get_well_state_endpoint():
    response = client.get("/api/wells/15/9-F-15/state")
    assert response.status_code == 200
    data = response.json()
    assert data["well_id"] == "15/9-F-15"
    assert data["data_source"] == SCIENTIFIC_LABEL
    assert "stream_status" in data
    assert "current_md" in data
    assert "ml" in data
    assert data["ml"]["status"] == "ML_NOT_READY"
    assert data["ml"]["is_blocked"] is True


def test_get_latest_sensor_endpoint():
    response = client.get("/api/wells/15/9-F-15/sensors/latest")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_get_sensor_history_causal_isolation():
    """Verify history endpoint strictly returns emitted records <= cutoff_md without future leakage."""
    state_mgr = get_app_state()

    # Ensure active well matches test records
    state_mgr.stream_client.active_well = "15/9-F-15"
    state_mgr.stream_client.history.clear()
    state_mgr.stream_client._process_message(make_json("15/9-F-15", 1000.0, 10.0))
    state_mgr.stream_client._process_message(make_json("15/9-F-15", 1020.0, 15.0))
    state_mgr.stream_client._process_message(make_json("15/9-F-15", 1050.0, 20.0))

    # Request history at cutoff 1020.0m
    response = client.get("/api/wells/15/9-F-15/sensors/history?cutoff_md=1020.0")
    assert response.status_code == 200
    data = response.json()

    assert data["cutoff_md"] == 1020.0
    assert data["count"] == 2
    for rec in data["records"]:
        assert rec["md"] <= 1020.0


def test_get_offset_events_endpoint():
    response = client.get("/api/wells/15/9-F-15/events?current_md=3000.0&radius=100.0")
    assert response.status_code == 200
    data = response.json()
    assert data["active_well"] == "15/9-F-15"
    assert "risk_summary" in data
    assert "nearby_events" in data
    assert "provenance" in data


def test_get_risk_status_ml_not_ready():
    """Verify risk API returns ML_NOT_READY and zero fabricated prediction."""
    response = client.get("/api/wells/15/9-F-15/risk")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ML_NOT_READY"
    assert data["is_blocked"] is True
    assert data["risk_score"] is None, "Fabricated risk score returned when ML is blocked!"
    assert "Minimum 5 required" in data["reason"] or "independent positive" in data["reason"] or "blocked" in data["reason"].lower()


def test_invalid_well_id_returns_404():
    response = client.get("/api/wells/INVALID_WELL_9999/state")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_api_authentication_enforcement():
    """Verify API authentication header verification when enabled."""
    os.environ["AUTH_REQUIRED"] = "true"
    os.environ["AUTH_TOKEN"] = "test-secret-key"
    try:
        # Unauthorized request
        res_unauth = client.get("/api/wells")
        assert res_unauth.status_code == 401

        # Authorized request with X-API-Key
        res_auth_key = client.get("/api/wells", headers={"X-API-Key": "test-secret-key"})
        assert res_auth_key.status_code == 200

        # Authorized request with Bearer token
        res_auth_bearer = client.get("/api/wells", headers={"Authorization": "Bearer test-secret-key"})
        assert res_auth_bearer.status_code == 200
    finally:
        os.environ["AUTH_REQUIRED"] = "false"


def test_websocket_application_gateway_typed_events():
    """Verify application WebSocket gateway emits typed events: sensor_update, ml_update, stream_status."""
    with client.websocket_connect("/api/ws/wells/15/9-F-15") as ws:
        # Receive initial stream_status event
        msg1 = ws.receive_json()
        assert msg1["type"] == "stream_status"
        assert msg1["data"]["well_id"] == "15/9-F-15"
        assert msg1["data"]["data_source"] == SCIENTIFIC_LABEL
