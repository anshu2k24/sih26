import pytest
from fastapi.testclient import TestClient
from ertmac.api.server import app
from ertmac.streaming.simulator import SensorStreamSimulator

@pytest.fixture
def client():
    return TestClient(app)


def test_simulator_standby_and_controls():
    """Verify SensorStreamSimulator defaults to standby (is_paused=True) until start is commanded."""
    sim = SensorStreamSimulator(autostart=False)
    assert sim.is_paused is True
    assert sim.is_running is False

    # Start digging
    sim.start_streaming(well_id="15/9-F-15", speed=50.0)
    assert sim.is_paused is False
    assert sim.active_well_id == "15/9-F-15"
    assert sim.speed == 50.0

    # Pause digging
    sim.pause_streaming()
    assert sim.is_paused is True

    # Resume digging
    sim.resume_streaming()
    assert sim.is_paused is False


def test_stream_control_endpoints(client):
    """Verify REST API stream control endpoints start, pause, resume, and report status."""
    # 1. Get status
    resp = client.get("/api/stream/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_streaming" in data
    assert "status" in data

    # 2. Start stream
    start_resp = client.post("/api/stream/start?well_id=15/9-F-15&speed=50.0")
    assert start_resp.status_code == 200
    assert start_resp.json()["success"] is True

    # Check status after start
    status_after_start = client.get("/api/stream/status").json()
    assert status_after_start["is_streaming"] is True

    # 3. Pause stream
    pause_resp = client.post("/api/stream/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["success"] is True

    # Check status after pause
    status_after_pause = client.get("/api/stream/status").json()
    assert status_after_pause["is_streaming"] is False

    # 4. Resume stream
    resume_resp = client.post("/api/stream/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["success"] is True

    status_after_resume = client.get("/api/stream/status").json()
    assert status_after_resume["is_streaming"] is True
