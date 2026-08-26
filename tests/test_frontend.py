import pytest
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_frontend_code_boundaries():
    app_path = REPO_ROOT / "app.py"
    assert app_path.exists(), "Frontend file missing"
    
    with open(app_path, "r") as f:
        content = f.read()
        
    # Check ML Status Panel presence
    assert "ML BLOCKED — NEED REAL DATA" in content, "Missing ML blocked status"
    assert "OIL/eRTMAC data not found" in content, "Missing ML blocked reason"
    
    # Check Placeholder presence
    assert "Predictive Risk" in content, "Missing predictive placeholder"
    
    # Check for NO predictions in historical section
    assert "predict" not in content.split("Historical NWIS Intelligence")[1].split("Predictive Risk")[0].lower(), "Found prediction text in historical intelligence section"
    assert "probability" not in content.split("Historical NWIS Intelligence")[1].split("Predictive Risk")[0].lower(), "Found probability text in historical intelligence section"
    
    # Check provenance fields are displayed
    assert "Source Record:" in content, "Missing provenance display"
    assert "Evidence:" in content, "Missing evidence display"

def test_api_responses_contain_no_predictions():
    # Load the API and test a response
    import sys
    sys.path.append(str(REPO_ROOT / "scripts"))
    from nwis_api import NWISHistoricalAPI
    
    verified_path = REPO_ROOT / "reports" / "tables" / "verified_event_episodes_v2.csv"
    api = NWISHistoricalAPI(str(verified_path))
    
    res = api.get_intelligence_by_depth("DUMMY", 3000.0, 100.0)
    
    # ensure no probability/prediction keys
    for k in res.keys():
        assert "predict" not in k.lower()
        assert "probab" not in k.lower()
        
    for ev in res["nearby_events"]:
        for k in ev.keys():
            assert "predict" not in k.lower()
            assert "probab" not in k.lower()
            
        # ensure provenance
        assert "source_ddr_record" in ev
        assert "primary_evidence" in ev
