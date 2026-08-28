import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from ertmac.streaming import (
    SensorRecord,
    CausalStreamBuffer,
    VolveReplaySensorSource,
    SyntheticSensorSource,
    ERTMACSensorSource,
    SensorStreamSimulator
)
from ertmac.ml.streaming_adapter import StreamInferenceAdapter
from ertmac.ml.features import CausalFeatureConfig
from ertmac.ml.models import PersistenceBaseline

REPO_ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = REPO_ROOT / "data" / "processed" / "usrop" / "usrop_clean.parquet"


def make_record(
    well_id: str = "15/9-F-15",
    timestamp: str = "2020-01-01T00:00:00Z",
    md: float = 1000.0,
    tvd: float = 950.0,
    rop: float = 15.0,
    wob: float = 5.0,
    rpm: float = 60.0,
    torque: float = 20.0,
    hookload: float = 120.0,
    spp: float = 10000.0,
    flow_in: float = 2000.0,
    mud_density: float = 1.2
) -> SensorRecord:
    return SensorRecord(
        well_id=well_id,
        timestamp=timestamp,
        md=md,
        tvd=tvd,
        rop=rop,
        wob=wob,
        rpm=rpm,
        torque=torque,
        hookload=hookload,
        spp=spp,
        flow_in=flow_in,
        mud_density=mud_density
    )


def test_sensor_record_to_feature_builder_integration():
    """1. Test SensorRecord -> causal DataFrame -> construct_causal_features integration."""
    buffer = CausalStreamBuffer(max_depth_span_m=200.0)
    adapter = StreamInferenceAdapter()

    records = [
        make_record(md=1000.0, rop=10.0, wob=5.0, rpm=60.0, spp=10000.0, flow_in=2000.0),
        make_record(md=1005.0, rop=12.0, wob=5.2, rpm=62.0, spp=10200.0, flow_in=2005.0),
        make_record(md=1010.0, rop=15.0, wob=5.5, rpm=65.0, spp=10500.0, flow_in=2010.0),
        make_record(md=1025.0, rop=18.0, wob=6.0, rpm=70.0, spp=11000.0, flow_in=2020.0),
    ]
    for r in records:
        buffer.append(r)

    result = adapter.process_causal_position(buffer, cutoff_md=1025.0)

    assert "features" in result
    features = result["features"]
    assert len(features) > 0, "No features constructed by existing feature builder"
    assert "rop_current" in features
    assert features["rop_current"] == 18.0
    assert "wob_mean_25.0m" in features


def test_only_emitted_causal_rows_used():
    """2. Test that ONLY emitted records <= cutoff_md are used by the adapter."""
    buffer = CausalStreamBuffer(max_depth_span_m=200.0)
    adapter = StreamInferenceAdapter()

    buffer.append(make_record(md=1000.0, rop=10.0))
    buffer.append(make_record(md=1025.0, rop=20.0))

    result = adapter.process_causal_position(buffer, cutoff_md=1025.0)
    features = result["features"]

    assert features["rop_current"] == 20.0
    assert result["cutoff_md"] == 1025.0


def test_future_md_cannot_enter_inference():
    """3. Test that future MD records (> cutoff_md) are strictly excluded and trigger leakage assertions."""
    buffer = CausalStreamBuffer(max_depth_span_m=200.0)
    adapter = StreamInferenceAdapter()

    buffer.append(make_record(md=1000.0, rop=10.0))
    buffer.append(make_record(md=1025.0, rop=20.0))
    buffer.append(make_record(md=1050.0, rop=30.0))

    # Request inference strictly at cutoff 1025.0m
    result = adapter.process_causal_position(buffer, cutoff_md=1025.0)
    features = result["features"]

    # Current ROP at cutoff 1025m MUST be 20.0, NOT 30.0 (which occurred at 1050m)
    assert features["rop_current"] == 20.0


def test_future_timestamps_cannot_enter_inference():
    """4. Test that records emitted after current stream position cannot leak into feature builder."""
    buffer = CausalStreamBuffer(max_depth_span_m=200.0)
    adapter = StreamInferenceAdapter()

    t0 = "2020-01-01T00:00:00Z"
    t1 = "2020-01-01T00:01:00Z"

    buffer.append(make_record(timestamp=t0, md=1000.0, rop=15.0))
    res0 = adapter.process_causal_position(buffer, cutoff_md=1000.0)

    # Append future record
    buffer.append(make_record(timestamp=t1, md=1050.0, rop=40.0))

    # Evaluate again at past cutoff 1000.0m
    res_past = adapter.process_causal_position(buffer, cutoff_md=1000.0)

    assert res0["features"]["rop_current"] == 15.0
    assert res_past["features"]["rop_current"] == 15.0


def test_correct_rolling_windows_passed_to_feature_builder():
    """5. Test that 5m, 10m, 25m, 50m depth windows are correctly constructed."""
    config = CausalFeatureConfig(windows=[5.0, 10.0, 25.0, 50.0])
    adapter = StreamInferenceAdapter(feature_config=config)
    buffer = CausalStreamBuffer(max_depth_span_m=200.0)

    # Populate 60m of continuous telemetry
    for depth in range(1000, 1060, 2):
        buffer.append(make_record(md=float(depth), rop=10.0 + (depth - 1000) * 0.1))

    result = adapter.process_causal_position(buffer, cutoff_md=1058.0)
    features = result["features"]

    for w in [5.0, 10.0, 25.0, 50.0]:
        assert f"rop_mean_{w}m" in features
        assert f"rop_delta_{w}m" in features


def test_ml_readiness_gate_is_respected():
    """6. Test that the existing ML readiness gate is respected and blocks inference when insufficient data."""
    adapter = StreamInferenceAdapter()
    buffer = CausalStreamBuffer()

    # Stream real rows from Volve source
    source = VolveReplaySensorSource(parquet_path=PARQUET_PATH)
    for rec in source.stream_records("15/9-F-15", start_md=1300.0, end_md=1350.0):
        buffer.append(rec)

    result = adapter.process_causal_position(buffer, cutoff_md=1340.0)

    assert result["is_blocked"] is True
    assert result["status"] == "ML_NOT_READY"
    assert "Minimum 5 required" in result["gate_reason"] or "independent positive" in result["gate_reason"]


def test_existing_prediction_output_schema_preserved():
    """7. Test that the prediction/gate output schema returns expected keys."""
    adapter = StreamInferenceAdapter()
    buffer = CausalStreamBuffer()
    buffer.append(make_record(md=1000.0, rop=10.0))

    result = adapter.process_causal_position(buffer, cutoff_md=1000.0)

    expected_keys = ["status", "is_blocked", "gate_reason", "cutoff_md", "well_id", "risk_score", "features"]
    for k in expected_keys:
        assert k in result, f"Missing result schema key: {k}"


def test_no_prediction_fabricated_when_ml_blocked():
    """8. Test that NO prediction is fabricated when ML is blocked by gate checks."""
    adapter = StreamInferenceAdapter()
    buffer = CausalStreamBuffer()
    buffer.append(make_record(md=1000.0, rop=10.0))

    result = adapter.process_causal_position(buffer, cutoff_md=1000.0)

    assert result["is_blocked"] is True
    assert result["risk_score"] is None, "Fabricated risk score returned when ML is blocked!"


def test_deterministic_replay_produces_deterministic_inference_features():
    """9. Test that deterministic replay produces identical causal features across repeated runs."""
    source = VolveReplaySensorSource(parquet_path=PARQUET_PATH)

    # Run 1
    sim1 = SensorStreamSimulator(source=source)
    adapter1 = StreamInferenceAdapter()
    for r in sim1.stream_sync("15/9-F-15", speed=10000.0, start_md=1300.0, end_md=1320.0):
        pass
    res1 = adapter1.process_causal_position(sim1.buffer, cutoff_md=1315.0)

    # Run 2
    sim2 = SensorStreamSimulator(source=source)
    adapter2 = StreamInferenceAdapter()
    for r in sim2.stream_sync("15/9-F-15", speed=10000.0, start_md=1300.0, end_md=1320.0):
        pass
    res2 = adapter2.process_causal_position(sim2.buffer, cutoff_md=1315.0)

    assert res1["features"] == res2["features"]
    assert res1["status"] == res2["status"]


def test_source_agnostic_adapter_with_synthetic_source():
    """Verify that StreamInferenceAdapter is source-agnostic and works with SyntheticSensorSource."""
    synth_source = SyntheticSensorSource(num_wells=1)
    buffer = CausalStreamBuffer()
    adapter = StreamInferenceAdapter()

    well_id = synth_source.get_available_wells()[0]
    records = list(synth_source.stream_records(well_id))
    for r in records[:50]:
        buffer.append(r)

    cutoff = records[25].md
    res = adapter.process_causal_position(buffer, cutoff_md=cutoff)
    assert res["status"] in ["ML_NOT_READY", "SUCCESS"]
    assert len(res["features"]) > 0
