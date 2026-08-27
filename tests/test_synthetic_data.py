import pytest
import pandas as pd
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from ertmac.ml.synthetic import build_synthetic_dataset

def test_synthetic_data_generation():
    df_e, df_s = build_synthetic_dataset(num_wells=8, seed=42)
    
    assert df_s['well_id'].nunique() == 8
    assert len(df_e) == 6 # We set first 6 wells to have events
    
    # Test schemas
    assert "rop" in df_s.columns
    assert "mud_density" in df_s.columns
    assert "event_type" in df_e.columns
    
    # Test text marker
    assert "[SYNTHETIC" in df_e.iloc[0]['primary_evidence']
    
    # Test no impossible negative values
    assert (df_s['rop'] >= 0).all()
    assert (df_s['spp'] >= 0).all()
    
    # Monotonic MD
    for _, group in df_s.groupby('well_id'):
        assert group['md'].is_monotonic_increasing
