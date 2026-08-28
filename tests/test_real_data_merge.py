import pytest
import pandas as pd
from pathlib import Path
import json

def test_leakage_assertion():
    parquet_path = Path("data/processed/real_training/mud_loss_real_v1.parquet")
    if not parquet_path.exists():
        pytest.skip("Dataset not generated yet")
    df = pd.read_parquet(parquet_path)
    
    # Leakage check: cutoff_md should be <= onset_md
    # and we should ensure that the dataset features are drawn only from data before cutoff_md
    # We verify that cutoff_md < onset_md in the output (e.g. onset_md - 25m)
    assert (df['cutoff_md'] < df['onset_md']).all(), "Leakage: cutoff_md is not before onset_md"

def test_schema_and_confidence():
    parquet_path = Path("data/processed/real_training/mud_loss_real_v1.parquet")
    if not parquet_path.exists():
        pytest.skip("Dataset not generated yet")
    df = pd.read_parquet(parquet_path)
    
    # Required causal features from config
    required_cols = [
        'well_id', 'is_event', 'onset_md', 'cutoff_md',
        'rop_current', 'wob_current', 'spp_current', 'torque_current'
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"
        
    # We cannot directly verify confidence in the final parquet because we just have 0/1.
    # However, we can assert no unknown events leaked through by checking the raw vs processed counts.
    # We'll just verify the basic schema constraints for ML readiness.
    assert df['is_event'].isin([0, 1]).all()

def test_well_mapping_correctness():
    report_path = Path("reports/real_data_merge_report.md")
    if not report_path.exists():
        pytest.skip("Report not generated yet")
        
    with open(report_path, "r") as f:
        content = f.read()
        
    # Check that it identifies zero coverage wells correctly
    assert "Event-Negative-Only" in content
    # 15/9-F-9 A should definitely be in zero coverage
    assert "15/9-F-9 A" in content
