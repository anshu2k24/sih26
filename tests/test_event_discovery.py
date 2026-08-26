import pytest
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TABLES_DIR = REPO_ROOT / "reports" / "tables"
CANDIDATES_PATH = TABLES_DIR / "event_candidates.csv"

@pytest.fixture
def candidates_df():
    assert CANDIDATES_PATH.exists(), "Event candidates table not found."
    return pd.read_csv(CANDIDATES_PATH)

def test_candidate_schema(candidates_df):
    expected_cols = [
        "event_id", "well_id", "wellbore_id", "event_type", "confidence",
        "source_object", "source_field", "text", "md", "tvd",
        "timestamp_start", "timestamp_end", "raw_code", "evidence_reason"
    ]
    for col in expected_cols:
        assert col in candidates_df.columns, f"Missing column: {col}"

def test_confidence_values(candidates_df):
    allowed_confidences = {"HIGH", "MEDIUM", "LOW"}
    unique_conf = set(candidates_df["confidence"].unique())
    assert unique_conf.issubset(allowed_confidences), f"Invalid confidence values found: {unique_conf - allowed_confidences}"

def test_provenance_preservation(candidates_df):
    # Ensure source object and field are documented
    assert not candidates_df["source_object"].isnull().any(), "Missing source_object provenance."
    assert not candidates_df["source_field"].isnull().any(), "Missing source_field provenance."
    # Ensure raw text is preserved
    assert not candidates_df["text"].isnull().all(), "Raw text was not preserved."

def test_duplicate_handling(candidates_df):
    # For now, duplicate events might just be multiple occurrences, but event_ids must be unique
    assert candidates_df["event_id"].is_unique, "event_ids are not unique."
