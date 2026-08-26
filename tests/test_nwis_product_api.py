import pytest
from pathlib import Path
import sys
import os

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "scripts"))
from nwis_api import NWISHistoricalAPI

VERIFIED_PATH = REPO_ROOT / "reports" / "tables" / "verified_event_episodes_v2.csv"

@pytest.fixture
def api():
    assert VERIFIED_PATH.exists()
    return NWISHistoricalAPI(str(VERIFIED_PATH))

def test_depth_window_correctness(api):
    res = api.get_intelligence_by_depth("DUMMY_WELL", 3000.0, radius=50.0)
    for ev in res["nearby_events"]:
        assert ev["depth_distance_m"] <= 50.0

def test_deterministic_ordering(api):
    res = api.get_intelligence_by_depth("DUMMY_WELL", 3000.0, radius=250.0)
    events = res["nearby_events"]
    # Check if sorted ascending by distance
    distances = [ev["depth_distance_m"] for ev in events]
    assert distances == sorted(distances)

def test_provenance_preservation(api):
    res = api.get_intelligence_by_depth("DUMMY_WELL", 3000.0, radius=250.0)
    for ev in res["nearby_events"]:
        assert "source_ddr_record" in ev
        assert ev["source_ddr_record"] is not None
        assert ev["primary_evidence"] is not None
    assert "provenance" in res
    assert "No generative AI claims used" in res["provenance"]

def test_no_hallucinated_fields(api):
    res = api.get_intelligence_by_depth("DUMMY_WELL", 3000.0, radius=50.0)
    assert "active_well" in res
    assert "risk_summary" in res
    assert "prediction" not in res.get("risk_summary", "").lower()
    assert "probability" not in res.get("risk_summary", "").lower()

def test_event_filtering(api):
    res = api.get_intelligence_by_depth("DUMMY_WELL", 3000.0, radius=250.0, event_type="FORMATION_MUD_LOSS")
    for ev in res["nearby_events"]:
        assert ev["event_type"] == "FORMATION_MUD_LOSS"

def test_empty_result_handling(api):
    res = api.get_intelligence_by_depth("DUMMY_WELL", 99999.0, radius=10.0)
    assert len(res["nearby_events"]) == 0
    assert "No historical evidence detected" in res["risk_summary"]

def test_score_reproducibility(api):
    res1 = api.get_intelligence_by_depth("DUMMY_WELL", 3000.0, radius=100.0)
    res2 = api.get_intelligence_by_depth("DUMMY_WELL", 3000.0, radius=100.0)
    assert res1["nearby_events"] == res2["nearby_events"]
