import pytest
import numpy as np
import pandas as pd
from ertmac.ml.sequence import extract_sequences

def test_extract_sequences():
    # Create dummy events and sensors
    df_events = pd.DataFrame({
        'wellbore_id': ['w1', 'w1'],
        'event_type': ['FORMATION_MUD_LOSS', 'FORMATION_MUD_LOSS'],
        'md': [100.0, 200.0]
    })
    
    # Create sensors
    mds = np.linspace(0, 300, 3000)
    df_sensors = pd.DataFrame({
        'wellbore_id': ['w1'] * 3000,
        'md': mds,
        'rop': np.random.randn(3000),
        'wob': np.random.randn(3000),
        'rpm': np.random.randn(3000),
        'torque': np.random.randn(3000),
        'hookload': np.random.randn(3000),
        'spp': np.random.randn(3000),
        'flow_in': np.random.randn(3000),
        'mud_density': np.random.randn(3000),
    })
    
    X, y, groups = extract_sequences(df_events, df_sensors, horizon=25.0, seq_length=50)
    
    # 2 positives, and negative sampling (ratio 5 means ~10 negatives)
    assert len(X) > 0
    assert X.shape[1] == 50
    assert X.shape[2] == 8 # channels
    
    assert len(y) == len(X)
    assert len(groups) == len(X)
    assert 'w1' in groups
    
    # Check no leakage: X sequences should not contain MDs > cutoff (onset - horizon)
    # The actual MD values are not in X (X only has sensor channels),
    # but the test checks the shape and length contract.
