import pytest
import pandas as pd
import numpy as np
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TABLES_DIR = REPO_ROOT / "reports" / "tables"
EVENTS_DIR = REPO_ROOT / "data" / "processed" / "events"

CTX_PATH = EVENTS_DIR / "event_context.parquet"
VERIFIED_PATH = TABLES_DIR / "verified_event_episodes_v2.csv"
CANDIDATES_PATH = TABLES_DIR / "event_candidates.csv"

@pytest.fixture
def df_ctx():
    assert CTX_PATH.exists()
    return pd.read_parquet(CTX_PATH)

@pytest.fixture
def df_ver():
    assert VERIFIED_PATH.exists()
    return pd.read_csv(VERIFIED_PATH)

@pytest.fixture
def df_cand():
    assert CANDIDATES_PATH.exists()
    return pd.read_csv(CANDIDATES_PATH)

def test_v2_positive_episodes_only(df_ctx, df_ver):
    ctx_eps = set(df_ctx['event_episode_id'].unique())
    ver_eps = set(df_ver[df_ver['is_verified_positive'] == True]['event_episode_id'].unique())
    assert ctx_eps.issubset(ver_eps), "Context table contains unverified episodes"

def test_no_missing_onset_md(df_ctx):
    assert df_ctx['onset_md'].notnull().all(), "Missing onset_md in context table"

def test_no_duplicate_event_episode_id(df_ver):
    assert df_ver['event_episode_id'].is_unique, "Duplicate event_episode_id found"

def test_no_post_onset_context_in_pre_event(df_ctx):
    pre = df_ctx[df_ctx['context_role'] == 'PRE_EVENT']
    
    # Distance to onset should be > 0 if defined
    if len(pre[pre['distance_to_onset_m'].notnull()]) > 0:
        assert (pre['distance_to_onset_m'].dropna() > 0).all(), "Post-onset MD found in PRE_EVENT context"
        
    # Time to onset should be > 0 if defined
    if len(pre[pre['time_to_onset_hours'].notnull()]) > 0:
        assert (pre['time_to_onset_hours'].dropna() > 0).all(), "Post-onset Timestamp found in PRE_EVENT context"

def test_raw_evidence_remains_traceable(df_ctx, df_cand):
    # Ensure all context_record_ids actually exist in the raw candidates
    ctx_ids = set(df_ctx['context_record_id'].unique())
    cand_ids = set(df_cand['event_id'].unique())
    assert ctx_ids.issubset(cand_ids), "Fabricated context_record_ids found!"

def test_well_ids_intact(df_ctx, df_cand):
    # Ensure well_ids are exactly from real data
    ctx_wells = set(df_ctx['well_id'].unique())
    cand_wells = set(df_cand['well_id'].unique())
    assert ctx_wells.issubset(cand_wells), "Fabricated well_ids found!"

def test_no_synthetic_rows(df_ctx, df_cand):
    # Total context rows should not exceed total candidate rows
    # Actually, a candidate might be used as context for multiple episodes if they share wellbore,
    # but the content must exactly match original rows.
    ctx_texts = set(df_ctx['raw_text'].dropna())
    cand_texts = set(df_cand['text'].dropna())
    assert ctx_texts.issubset(cand_texts), "Synthetic raw text generated!"
