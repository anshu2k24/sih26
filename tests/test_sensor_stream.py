import pytest
import os
import json
import asyncio
import socket
from pathlib import Path

from ertmac.streaming import (
    SensorRecord,
    CausalStreamBuffer,
    VolveReplaySensorSource,
    SensorStreamSimulator,
    SensorWebSocketServer,
    SCIENTIFIC_LABEL
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = REPO_ROOT / "data" / "processed" / "usrop" / "usrop_clean.parquet"


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 0))
        return s.getsockname()[1]


def test_sensor_record_schema_contract():
    rec = SensorRecord(
        well_id="15/9-F-15",
        timestamp="2020-01-01T00:00:00Z",
        md=1000.0,
        tvd=950.0,
        rop=15.5,
        wob=4.2,
        rpm=60.0,
        torque=12.0,
        hookload=120.0,
        spp=20000.0,
        flow_in=2000.0,
        mud_density=1.2
    )
    d = rec.to_dict()
    assert d["well_id"] == "15/9-F-15"
    assert d["md"] == 1000.0
    assert d["rop"] == 15.5

    restored = SensorRecord.from_dict(d)
    assert restored.well_id == rec.well_id
    assert restored.md == rec.md


def test_causal_stream_buffer_isolation_and_bounds():
    buffer = CausalStreamBuffer(max_depth_span_m=200.0)

    # Append sequential records
    buffer.append(SensorRecord("15/9-F-15", "2020-01-01T00:00:00Z", md=1000.0, rop=10.0))
    buffer.append(SensorRecord("15/9-F-15", "2020-01-01T00:00:10Z", md=1100.0, rop=15.0))
    buffer.append(SensorRecord("15/9-F-15", "2020-01-01T00:00:20Z", md=1250.0, rop=20.0))

    # Test strictly emitted history <= cutoff_md (Zero Future Data Leakage)
    causal_sub = buffer.get_history_at_cutoff(cutoff_md=1100.0)
    assert len(causal_sub) == 1
    assert causal_sub[-1].md == 1100.0


def test_volve_replay_source_parquet():
    assert PARQUET_PATH.exists(), f"Parquet dataset missing at {PARQUET_PATH}"
    source = VolveReplaySensorSource(parquet_path=PARQUET_PATH)

    wells = source.get_available_wells()
    assert len(wells) > 0
    assert "15/9-F-15" in wells

    # Stream records
    records = list(source.stream_records("15/9-F-15", start_md=1300.0, end_md=1350.0))
    assert len(records) > 0


def test_sensor_stream_simulator_replay():
    source = VolveReplaySensorSource(parquet_path=PARQUET_PATH)
    simulator = SensorStreamSimulator(source=source)

    replayed = list(simulator.stream_sync("15/9-F-15", speed=10000.0, start_md=1300.0, end_md=1350.0))
    assert len(replayed) > 0
    assert simulator.state.emitted_count == len(replayed)
    assert simulator.state.data_label == SCIENTIFIC_LABEL


def test_websocket_server_broadcasting():
    """Verify WebSocket server starts, broadcasts 1 JSON message per record, and handles disconnect cleanly."""
    import websockets

    async def _test_impl():
        source = VolveReplaySensorSource(parquet_path=PARQUET_PATH)
        simulator = SensorStreamSimulator(source=source)
        port = get_free_port()
        server = SensorWebSocketServer(simulator=simulator, host="localhost", port=port)

        await server.start()

        try:
            # Connect test client
            async with websockets.connect(f"ws://localhost:{port}") as ws:
                # Receive welcome banner
                banner_raw = await ws.recv()
                banner = json.loads(banner_raw)
                assert banner["status"] == "CONNECTED"
                assert banner["data_source_label"] == SCIENTIFIC_LABEL

                # Run stream in background task
                stream_task = asyncio.create_task(
                    server.run_stream(well_id="15/9-F-15", speed=10000.0, start_md=1300.0, end_md=1320.0)
                )

                # Receive sensor record JSON payload
                msg_raw = await ws.recv()
                rec = json.loads(msg_raw)

                assert rec["well_id"] == "15/9-F-15"
                assert "md" in rec
                assert "rop" in rec

                await stream_task
        finally:
            await server.stop()

    asyncio.run(_test_impl())
