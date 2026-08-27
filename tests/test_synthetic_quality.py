import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from ertmac.ml.synthetic_evaluation import calculate_structural_validity, calculate_physical_plausibility, calculate_statistical_realism

def test_structural_validity():
    df_sensors = pd.DataFrame(columns=["well_id", "timestamp", "md", "rop", "wob", "rpm", "torque", "hookload", "spp", "flow_in", "mud_density"])
    df_events = pd.DataFrame(columns=["well_id", "wellbore_id", "independent_well_group", "timestamp", "md", "event_type"])
    
    # Needs some actual data for well count to be > 0
    df_sensors = pd.DataFrame({"well_id": ["W1", "W2", "W3", "W4", "W5"]})
    for col in ["timestamp", "md", "rop", "wob", "rpm", "torque", "hookload", "spp", "flow_in", "mud_density"]:
        df_sensors[col] = 1.0
        
    df_events = pd.DataFrame({
        "well_id": ["W1", "W2", "W3", "W4", "W5"],
        "wellbore_id": ["W1", "W2", "W3", "W4", "W5"],
        "independent_well_group": ["W1", "W2", "W3", "W4", "W5"],
        "timestamp": [1, 2, 3, 4, 5],
        "md": [1, 2, 3, 4, 5],
        "event_type": ["E"]*5
    })
    
    res = calculate_structural_validity(df_events, df_sensors)
    assert res["Schema Contract"] == 10.0
    assert res["Causal/Leakage Integrity"] == 10.0
    assert res["LOWO/Well Diversity"] == 10.0 # 5 wells + 5 groups

def test_physical_plausibility():
    df_sensors = pd.DataFrame({
        "well_id": ["W1", "W1"],
        "timestamp": [1, 2],
        "md": [10.0, 20.0],
        "rop": [10.0, 20.0],
        "wob": [5.0, 5.0],
        "rpm": [100.0, 100.0],
        "spp": [1000.0, -1000.0], # Negative SPP!
        "flow_in": [500.0, 500.0],
        "mud_density": [1.2, 1.2]
    })
    
    res = calculate_physical_plausibility(df_sensors)
    # Range Plausibility loses 2 points for negative SPP
    assert res["Range Plausibility"] == 18.0
    assert res["Temporal/Depth Continuity"] == 20.0

def test_statistical_realism():
    x1 = np.array([1, -1, 1, -1] * 25) # 100 length
    x2 = np.array([1, 1, -1, -1] * 25) # 100 length
    df_sensors = pd.DataFrame({
        "well_id": ["W1"]*100,
        "spp": np.linspace(1000, 900, 100), # Perfect linear ramp
        "flow_in": x1, # Uncorrelated to SPP (which is linear, x1 is alternating, correlation very low)
        "wob": x1,
        "torque": x2
    })
    df_events = pd.DataFrame({"well_id": ["W1"], "event_type": ["E"]})
    
    res = calculate_statistical_realism(df_events, df_sensors)
    # SPP and flow_in not correlated, wob and torque not correlated -> loses 10 pts
    assert res["Cross-channel Correlation"] == 0.0
    # Perfect linear ramp means diffs are identical -> mode count > 5% -> loses 7 pts
    assert res["Event Precursor Realism"] == 3.0
