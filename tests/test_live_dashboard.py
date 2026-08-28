import pytest
import json
import asyncio
import time
from pathlib import Path

from ertmac.streaming import (
    SensorRecord,
    VolveReplaySensorSource,
    SensorStreamSimulator,
    SensorWebSocketServer,
    SensorStreamClient,
    SCIENTIFIC_LABEL
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = REPO_ROOT / "data" / "processed" / "usrop" / "usrop_clean.parquet"


def test_live_dashboard_websocket_client_integration():
    """Tests 1, 2, 3, 4, 7, 8, 9, 10, 11: End-to-end WebSocket -> SensorStreamClient state integration."""
    source = VolveReplaySensorSource(parquet_path=PARQUET_PATH)
    simulator = SensorStreamSimulator(source=source)
    port = 8775
    server = SensorWebSocketServer(simulator=simulator, host="localhost", port=port)

    async def _test_flow():
        await server.start()

        client = SensorStreamClient(host="localhost", port=port)
        client.start()

        # Wait for client connection
        for _ in range(20):
            if client.status == "LIVE":
                break
            await asyncio.sleep(0.1)

        assert client.status == "LIVE", "Client failed to connect to WebSocket server"

        # Stream records asynchronously from well 15/9-F-15
        stream_task = asyncio.create_task(
            server.run_stream("15/9-F-15", speed=10000.0, start_md=1300.0, end_md=1320.0)
        )

        await stream_task
        await asyncio.sleep(0.2)

        state = client.get_state()

        # 1. State Label & Distinction (Test 11)
        assert state["data_source_label"] == SCIENTIFIC_LABEL
        assert state["status"] == "LIVE"

        # 2. Well ID, MD, TVD, Timestamp, Message Count (Tests 2, 3, 4)
        assert state["well_id"] == "15/9-F-15"
        assert state["current_md"] > 1300.0
        assert state["tvd"] is not None
        assert state["samples_received"] > 0

        # 3. Real Sensor Values in Current Record (Test 9)
        rec = state["current_record"]
        assert rec is not None
        assert rec["well_id"] == "15/9-F-15"
        assert "rop" in rec
        assert "wob" in rec
        assert "rpm" in rec
        assert "torque" in rec
        assert "hookload" in rec
        assert "spp" in rec

        # 4. No Future Rows Displayed (Test 10)
        history = state["history"]
        assert len(history) > 0
        max_md = state["current_md"]
        for h in history:
            assert h["md"] <= max_md

        # 5. ML_NOT_READY and No Fake Prediction (Tests 7, 8)
        ml_res = state["ml_result"]
        assert ml_res["status"] == "ML_NOT_READY"
        assert ml_res["is_blocked"] is True
        assert ml_res["risk_score"] is None, "Fake prediction generated when ML is blocked!"
        assert "Minimum 5 required" in ml_res["gate_reason"] or "independent positive" in ml_res["gate_reason"]

        client.stop()
        await server.stop()

    asyncio.run(_test_flow())


def test_disconnect_and_reconnect_behavior():
    """Tests 5 & 6: Disconnect state ('STREAM DISCONNECTED') and automatic reconnect state ('LIVE')."""
    source = VolveReplaySensorSource(parquet_path=PARQUET_PATH)
    simulator = SensorStreamSimulator(source=source)
    port = 8776
    server = SensorWebSocketServer(simulator=simulator, host="localhost", port=port)

    async def _test_reconnect():
        await server.start()

        client = SensorStreamClient(host="localhost", port=port)
        client.start()

        # Connect
        for _ in range(20):
            if client.status == "LIVE":
                break
            await asyncio.sleep(0.1)

        assert client.status == "LIVE"

        # Shutdown server to trigger disconnect (Test 5)
        await server.stop()
        await asyncio.sleep(0.5)

        assert client.status == "STREAM DISCONNECTED"
        assert client.get_state()["ml_result"]["is_blocked"] is True

        # Restart server to trigger automatic reconnect (Test 6)
        server2 = SensorWebSocketServer(simulator=simulator, host="localhost", port=port)
        await server2.start()

        for _ in range(30):
            if client.status == "LIVE":
                break
            await asyncio.sleep(0.1)

        assert client.status == "LIVE"

        client.stop()
        await server2.stop()

    asyncio.run(_test_reconnect())
