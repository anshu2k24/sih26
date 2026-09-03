import os
os.environ["AUTH_REQUIRED"] = "false"
import sys
import json
from pathlib import Path

ROOT = Path("src").resolve()
sys.path.insert(0, str(ROOT))
SCRIPTS = Path("scripts").resolve()
sys.path.insert(0, str(SCRIPTS))

from dotenv import load_dotenv
load_dotenv()

from fastapi.testclient import TestClient
from ertmac.api.server import app, get_app_state

def test_ws_telemetry_delivery():
    client = TestClient(app)
    state_mgr = get_app_state()

    # Feed a sensor record into the stream client
    test_rec = {
        "well_id": "15/9-F-15",
        "timestamp": "2020-01-01T00:00:00Z",
        "md": 1500.0,
        "tvd": 1450.0,
        "rop": 25.5,
        "wob": 12.0,
        "rpm": 120.0,
        "torque": 15.0,
        "hookload": 130.0,
        "spp": 15000.0,
        "flow_in": 2500.0,
        "mud_density": 1.25
    }
    state_mgr.stream_client._process_message(json.dumps(test_rec))

    with client.websocket_connect("/api/ws/wells/15/9-F-15") as websocket:
        # 1. First message: stream_status
        msg1 = websocket.receive_json()
        assert msg1["type"] == "stream_status"
        assert msg1["data"]["samples_received"] >= 1
        assert msg1["data"]["current_md"] == 1500.0

        # 2. Second message: sensor_update (sent immediately on connect)
        msg2 = websocket.receive_json()
        assert msg2["type"] == "sensor_update"
        assert msg2["data"]["md"] == 1500.0
        assert msg2["data"]["rop"] == 25.5

        # 3. Third message: ml_update
        msg3 = websocket.receive_json()
        assert msg3["type"] == "ml_update"

if __name__ == "__main__":
    test_ws_telemetry_delivery()
    print("PASS: WebSocket telemetry delivered successfully!")
