import pytest
import re
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_frontend_demo_boundaries():
    app_path = REPO_ROOT / "app.py"
    assert app_path.exists(), "Frontend file missing"
    
    with open(app_path, "r") as f:
        content = f.read()
        
    # Check ML Status Panel presence
    assert "ML BLOCKED — NEED REAL DATA" in content
    assert "data/raw/oil_ertmac_sensors.parquet" in content
    

    

    
    # Check NO predictions in historical section
    historical_section = content.split("Historical NWIS Intelligence")[1].split("Predictive Risk")[0]
    assert "predict" not in historical_section.lower()
    assert "probabilit" not in historical_section.lower()

def test_demo_api_contracts():
    sys.path.append(str(REPO_ROOT / "scripts"))
    from nwis_api import NWISHistoricalAPI
    
    verified_path = REPO_ROOT / "reports" / "tables" / "verified_event_episodes_v2.csv"
    api = NWISHistoricalAPI(str(verified_path))
    
    # Test Mud-loss proximity demo logic
    res = api.get_intelligence_by_depth("NO 15/9-19 ST2", 2900.0, 150.0, "FORMATION_MUD_LOSS")
    
    # Verify deterministic output
    assert res["active_well"] == "NO 15/9-19 ST2"
    assert "predict" not in res["risk_summary"].lower()
    
    for ev in res["nearby_events"]:
        assert ev["event_type"] == "FORMATION_MUD_LOSS"
        # Check depth distance correctly calculated
        assert abs(ev["onset_md"] - 2900.0) == ev["depth_distance_m"]
        assert ev["depth_distance_m"] <= 150.0
        # Check provenance
        assert "source_ddr_record" in ev
        assert "primary_evidence" in ev
