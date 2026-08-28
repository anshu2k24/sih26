import pytest
import pandas as pd
from ertmac.ml.inference import DataQualityGate

def test_distant_gap_clean_immediate_window():
    """
    Regression test for the quality gate scoping bug.
    A gap > max_gap_md (e.g. 10m) that is FAR outside the causal window 
    (e.g., 500m away) should NOT fail the gate if the immediate 25m 
    window is clean.
    """
    gate = DataQualityGate(required_history_md=25.0, max_gap_md=10.0)
    
    current_md = 1000.0
    
    mds = list(range(0, 500)) + list(range(970, 1001))
    
    df = pd.DataFrame({
        'md': mds,
        'wellbore_id': 'NO 1',
        'rop': 10.0,
        'wob': 10.0,
        'rpm': 100.0,
        'torque': 10.0,
        'hookload': 100.0,
        'spp': 2000.0,
        'flow_in': 500.0,
        'mud_density': 1.2
    })
    
    status = gate.check_quality(df, current_md, 'NO 1')
    assert status == "PASS", f"Gate should pass, but got {status}"
