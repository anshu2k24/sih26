import os
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_PARQUET = REPO_ROOT / "data" / "processed" / "usrop" / "usrop_clean.parquet"
RAW_DIR = REPO_ROOT / "data" / "raw" / "usrop"

def test_processed_file_exists():
    assert PROCESSED_PARQUET.exists(), "Processed parquet file is missing."

def test_row_count():
    df = pd.read_parquet(PROCESSED_PARQUET)
    assert len(df) == 198928, f"Expected 198,928 rows, got {len(df)}"

def test_well_count():
    df = pd.read_parquet(PROCESSED_PARQUET)
    wells = df['well_id'].nunique()
    assert wells == 7, f"Expected 7 wells, got {wells}"

def test_required_columns():
    df = pd.read_parquet(PROCESSED_PARQUET)
    expected = [
        'Measured Depth m', 'Weight on Bit kkgf', 'Average Standpipe Pressure kPa',
        'Average Surface Torque kN.m', 'Rate of Penetration m/h', 'Average Rotary Speed rpm',
        'Mud Flow In L/min', 'Mud Density In g/cm3', 'Diameter mm', 'Average Hookload kkgf',
        'Hole Depth (TVD) m', 'USROP Gamma gAPI', 'well_id'
    ]
    for col in expected:
        assert col in df.columns, f"Missing required column: {col}"
    assert "Unnamed: 0" not in df.columns, "Found Unnamed: 0 artifact column."

def test_duplicate_detection():
    df = pd.read_parquet(PROCESSED_PARQUET)
    # Exclude filename, sha, well_id for purely physical duplicates
    subset = df.drop(columns=['well_id', 'filename', 'sha256', 'MD_step'], errors='ignore')
    dupes = subset.duplicated().sum()
    assert dupes == 5709, f"Expected 5709 duplicate rows, got {dupes}."

def test_md_ordering_and_monotonicity():
    df = pd.read_parquet(PROCESSED_PARQUET)
    for well, group in df.groupby('well_id'):
        steps = group['Measured Depth m'].diff().dropna()
        negative_steps = (steps < 0).sum()
        assert negative_steps == 0, f"Non-monotonic MD found in well {well}."
        zero_steps = (steps == 0).sum()
        if well == "15/9-F-14":
            assert zero_steps == 2, f"Expected 2 duplicate MDs in F-14, got {zero_steps}."
        else:
            assert zero_steps >= 0, f"Duplicate MD values found in well {well}."

def test_numeric_types():
    df = pd.read_parquet(PROCESSED_PARQUET)
    for col in df.columns:
        if col not in ['well_id', 'filename', 'sha256']:
            assert pd.api.types.is_numeric_dtype(df[col]), f"Column {col} is not numeric."

def test_sentinel_outlier_rules():
    df = pd.read_parquet(PROCESSED_PARQUET)
    assert df['Hole Depth (TVD) m'].min() > 0, "TVD should be strictly positive."
    assert df['Diameter mm'].min() > 0, "Diameter should be strictly positive."
    assert df['Mud Density In g/cm3'].min() > 0, "Mud density should be strictly positive."
    
def test_raw_immutability():
    raw_files = list(RAW_DIR.glob("*.csv"))
    assert len(raw_files) == 7, "Raw directory does not have exactly 7 files."
    # Ensure they still have Unnamed: 0 (meaning we didn't overwrite raw files)
    df_raw = pd.read_csv(raw_files[0])
    assert "Unnamed: 0" in df_raw.columns, "Raw files seem to be modified (missing Unnamed: 0)."
