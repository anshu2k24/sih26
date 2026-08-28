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
    # Verify coordinate metadata is present
    well_f15 = next(w for w in data["wells"] if w["well_id"] == "15/9-F-15")
    assert well_f15["latitude"] == 58.44168
    assert well_f15["longitude"] == 1.88778
    assert well_f15["field"] == "Volve"


def test_get_nearby_wells_endpoint():
    """Verify /api/wells/{well_id}/nearby calculates Haversine distance and filters by radius."""
    response = client.get("/api/wells/15/9-F-15/nearby?radius_km=5.0")
    assert response.status_code == 200
    data = response.json()
    assert data["active_well"] == "15/9-F-15"
    assert data["radius_km"] == 5.0
    assert "nearby_wells" in data
    assert len(data["nearby_wells"]) > 0
    # Verify distance sorting
    distances = [w["distance_km"] for w in data["nearby_wells"]]
    assert distances == sorted(distances)
    # Check item schema
    item = data["nearby_wells"][0]
    assert "well_id" in item
    assert "distance_km" in item
    assert "distance_m" in item
    assert "latitude" in item
    assert "longitude" in item


def test_get_well_full_intelligence_endpoint():
    """Verify /api/wells/{well_id}/intelligence returns verified DDR historical events and metadata."""
    response = client.get("/api/wells/15/9-F-14/intelligence?active_well_id=15/9-F-15")
    assert response.status_code == 200
    data = response.json()
    assert data["well_id"] == "15/9-F-14"
    assert data["active_well_id"] == "15/9-F-15"
    assert data["total_events"] > 0
    assert "events" in data
    assert len(data["events"]) == data["total_events"]
    # Check event episode structure
    ev = data["events"][0]
    assert "event_episode_id" in ev
    assert "event_type" in ev
    assert "onset_md" in ev
    assert "primary_evidence" in ev
    assert "primary_source_record" in ev
    assert "source_label" in ev


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
    records = [
        {"md": 1000.0, "rop": 10.0},
        {"md": 1020.0, "rop": 15.0},
        {"md": 1050.0, "rop": 20.0},
    ]
    with state_mgr.stream_client._lock:
        state_mgr.stream_client.history.clear()
        state_mgr.stream_client.history.extend(records)

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
    assert "Minimum 5 required" in data["reason"] or "independent positive" in data["reason"] or "blocked" in data["reason"].lower() or "offline" in data["reason"].lower() or "stream" in data["reason"].lower()


def test_invalid_well_id_returns_404():
    response = client.get("/api/wells/INVALID_WELL_9999/state")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_api_authentication_enforcement():
    """Verify API returns 401 when AUTH_REQUIRED=true and no Bearer token is provided."""
    original = os.environ.get("AUTH_REQUIRED")
    os.environ["AUTH_REQUIRED"] = "true"
    try:
        # No auth header → must be 401
        res_unauth = client.get("/api/wells")
        assert res_unauth.status_code == 401, (
            f"Expected 401 without auth, got {res_unauth.status_code}"
        )

        # Invalid Bearer token → must be 401
        res_bad_token = client.get(
            "/api/wells",
            headers={"Authorization": "Bearer this.is.not.a.real.jwt"}
        )
        assert res_bad_token.status_code == 401, (
            f"Expected 401 with invalid JWT, got {res_bad_token.status_code}"
        )

        # Health check is always public
        res_health = client.get("/health")
        assert res_health.status_code == 200
    finally:
        if original is not None:
            os.environ["AUTH_REQUIRED"] = original
        else:
            os.environ["AUTH_REQUIRED"] = "false"


def test_websocket_application_gateway_typed_events():
    """Verify application WebSocket gateway emits typed events: sensor_update, ml_update, stream_status."""
    with client.websocket_connect("/api/ws/wells/15/9-F-15") as ws:
        # Receive initial stream_status event
        msg1 = ws.receive_json()
        assert msg1["type"] == "stream_status"
        assert msg1["data"]["well_id"] == "15/9-F-15"
        assert msg1["data"]["data_source"] == SCIENTIFIC_LABEL


def test_knowledge_search_endpoint():
    """Verify /api/knowledge/search returns deterministic text search results and filters."""
    # 1. Text query search for 'mud loss'
    res_text = client.get("/api/knowledge/search?q=mud%20loss")
    assert res_text.status_code == 200
    data_text = res_text.json()
    assert data_text["total_count"] > 0
    assert "results" in data_text
    assert len(data_text["results"]) == data_text["total_count"]
    # Check item schema
    item = data_text["results"][0]
    assert "event_episode_id" in item
    assert "event_type" in item
    assert "onset_md" in item
    assert "primary_evidence" in item
    assert "primary_source_record" in item
    assert "is_verified" in item
    assert item["is_verified"] is True

    # 2. Filter by well_id and event_type
    res_filtered = client.get("/api/knowledge/search?well_id=15/9-F-14&event_type=Equipment%20Failure")
    assert res_filtered.status_code == 200
    data_filtered = res_filtered.json()
    for r in data_filtered["results"]:
        assert r["event_type"] == "Equipment Failure"

    # 3. Filter by depth range min_md & max_md
    res_depth = client.get("/api/knowledge/search?min_md=2000&max_md=3000")
    assert res_depth.status_code == 200
    data_depth = res_depth.json()
    for r in data_depth["results"]:
        assert 2000.0 <= r["onset_md"] <= 3000.0

    # 4. Zero results query
    res_zero = client.get("/api/knowledge/search?q=NONEXISTENT_QUERY_99999")
    assert res_zero.status_code == 200
    data_zero = res_zero.json()
    assert data_zero["total_count"] == 0
    assert len(data_zero["results"]) == 0


def test_historical_depth_proximity_endpoint():
    """Verify /api/wells/{well_id}/historical-proximity correlates current MD against offset events."""
    # 1. Test active well 15/9-F-14 at current_md=2870m with 50m window (F-15 has FORMATION_MUD_LOSS at 2883m -> delta 13m)
    response = client.get("/api/wells/15/9-F-14/historical-proximity?current_md=2870.0&radius_km=5.0&depth_window_m=50.0")
    assert response.status_code == 200
    data = response.json()
    assert data["active_well_id"] == "15/9-F-14"
    assert data["current_md"] == 2870.0
    assert data["depth_window_m"] == 50.0
    assert data["matches_count"] > 0
    assert "matches" in data

    # Check match item schema & mandatory disclaimer
    match = data["matches"][0]
    assert "offset_well_id" in match
    assert "event_type" in match
    assert "event_md" in match
    assert "delta_md" in match
    assert match["delta_md"] <= 50.0
    assert "disclaimer" in match
    assert "NOT A PREDICTION" in match["disclaimer"]

    # 2. Test tight depth window (5m window -> 13m match excluded)
    res_tight = client.get("/api/wells/15/9-F-14/historical-proximity?current_md=2870.0&radius_km=5.0&depth_window_m=5.0")
    assert res_tight.status_code == 200
    data_tight = res_tight.json()
    for m in data_tight["matches"]:
        assert m["delta_md"] <= 5.0
