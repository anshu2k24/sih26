import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from ertmac.ml.normalization import (
    normalize_columns, handle_sentinels_and_impossible, 
    ensure_canonical, CANONICAL_EVENTS, CANONICAL_SENSORS
)

def test_normalize_columns():
    df = pd.DataFrame({
        " Well Name ": ["A"],
        "Date_Time": ["B"],
        "rate_of_penetration": [10.0]
    })
    norm = normalize_columns(df)
    assert "well_id" in norm.columns
    assert "timestamp" in norm.columns
    assert "rop" in norm.columns

def test_handle_sentinels_and_impossible():
    df = pd.DataFrame({
        "md": [100.0, -50.0, 20000.0, 150.0],
        "rop": [10.0, -999.25, -5.0, 20.0]
    })
    clean, rep = handle_sentinels_and_impossible(df, is_sensor=True)
    
    # MD checks
    assert not np.isnan(clean["md"].iloc[0])
    assert np.isnan(clean["md"].iloc[1]) # negative MD
    assert np.isnan(clean["md"].iloc[2]) # impossible MD > 15000
    
    # Sensor checks
    assert not np.isnan(clean["rop"].iloc[0])
    assert np.isnan(clean["rop"].iloc[1]) # -999.25 sentinel
    assert np.isnan(clean["rop"].iloc[2]) # negative physical sensor FLAGGED as NaN, NOT CLAMPED!
    
    assert rep["rop_negative"] == 1
    assert rep["md_impossible"] == 2
    assert rep["rop_sentinels"] == 1

def test_ensure_canonical():
    df = pd.DataFrame({"well_id": ["A"], "rop": [10.0]})
    can = ensure_canonical(df, CANONICAL_SENSORS)
    assert list(can.columns) == CANONICAL_SENSORS
    assert can["well_id"].iloc[0] == "A"
    assert can["rop"].iloc[0] == 10.0
    assert np.isnan(can["wob"].iloc[0]) # missing channel filled with NaN
