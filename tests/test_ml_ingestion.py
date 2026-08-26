import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from ertmac.ml.ingestion import IngestionValidator

@pytest.fixture
def validator():
    return IngestionValidator()

def test_missing_columns(validator):
    df_bad = pd.DataFrame({"well_id": [1, 2]})
    with pytest.raises(ValueError, match="missing required columns"):
        validator.validate_event_data(df_bad)

def test_duplicate_and_monotonic(validator):
    df = pd.DataFrame({
        "well_id": ["A", "A", "A"],
        "wellbore_id": ["A", "A", "A"],
        "timestamp": [1, 2, 2], # Duplicate time for A
        "md": [100.0, 110.0, 105.0], # Non-monotonic
        "tvd": [100.0, 110.0, 105.0],
        "rop": [1,2,3], "wob": [1,2,3], "rpm": [1,2,3], 
        "torque": [1,2,3], "hookload": [1,2,3], "spp": [1,2,3],
        "flow_in": [1,2,3], "mud_density": [1,2,3]
    })
    
    rep = validator.validate_sensor_data(df)
    assert rep["non_monotonic_depth_steps"] == 1
    assert rep["duplicate_rows"] == 0 # we check exact row dups for subset

def test_check_readiness_insufficient_wells(validator):
    df_evt = pd.DataFrame({
        "well_id": ["W1", "W2"],
        "event_type": ["FORMATION_MUD_LOSS", "FORMATION_MUD_LOSS"]
    })
    is_ready, msg = validator.check_readiness(df_evt, pd.DataFrame())
    assert not is_ready
    assert "Minimum 5 required" in msg

def test_check_readiness_insufficient_history(validator):
    # 5 wells, but sensor data doesn't reach onset - 25m
    wells = [f"W{i}" for i in range(5)]
    df_evt = pd.DataFrame({
        "well_id": wells,
        "event_type": ["FORMATION_MUD_LOSS"] * 5,
        "md": [1000.0] * 5
    })
    # Sensor data starts at 990 (doesn't reach 975)
    df_sensor = pd.DataFrame({
        "well_id": wells,
        "md": [990.0] * 5
    })
    is_ready, msg = validator.check_readiness(df_evt, df_sensor)
    assert not is_ready
    assert "Telemetry does not reach" in msg

def test_check_readiness_success(validator):
    wells = [f"W{i}" for i in range(5)]
    df_evt = pd.DataFrame({
        "well_id": wells,
        "event_type": ["FORMATION_MUD_LOSS"] * 5,
        "md": [1000.0] * 5
    })
    # Sensor data starts at 900 (well before 975)
    df_sensor = pd.DataFrame({
        "well_id": wells,
        "md": [900.0] * 5
    })
    is_ready, msg = validator.check_readiness(df_evt, df_sensor)
    assert is_ready
    assert "READY_FOR_FIRST_ML_EXPERIMENT" in msg
