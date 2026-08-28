import pytest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "scripts"))
sys.path.append(str(REPO_ROOT / "src"))

from nwis_api import NWISHistoricalAPI
from ertmac.ml.ingestion import IngestionValidator
from ertmac.nwis.geospatial import GeospatialIntelligence

def test_e2e_historical_intelligence():
    """
    Simulates an end-to-end user query entering the NWIS system.
    Active Well -> Current MD -> API Query -> Deterministic Filtering -> Safe JSON Response.
    """
    verified_path = REPO_ROOT / "reports" / "tables" / "verified_event_episodes_v2.csv"
    assert verified_path.exists(), "Verified Volve taxonomy missing"
    
    api = NWISHistoricalAPI(str(verified_path))
    
    # 1. User is drilling well 'NO 15/9-19 ST2' at 2950m.
    active_well = "NO 15/9-19 ST2"
    current_md = 2950.0
    radius = 100.0
    
    # 2. API executes backend retrieval.
    result = api.get_intelligence_by_depth(active_well, current_md, radius)
    
    # 3. Verify System State constraints
    assert result['active_well'] == active_well
    assert "predict" not in result['risk_summary'].lower()
    
    # 4. Verify historical offsets were correctly found (e.g., Mud Loss at 3018m is 68m away)
    found_events = result['nearby_events']
    assert len(found_events) > 0
    
    for ev in found_events:
        # Distance must be <= 100m
        assert ev['depth_distance_m'] <= 100.0
        # Provenance must be intact
        assert ev['source_ddr_record'] is not None

def test_e2e_ml_ingestion_blocker():
    """
    Simulates the system attempting to transition from Historical NWIS to Predictive ML.
    It hits the ingestion gate and MUST safely fail (BLOCKED) because real OIL data isn't present.
    """
    validator = IngestionValidator()
    
    events_path = REPO_ROOT / "data" / "raw" / "oil_ertmac_events.parquet"
    
    # Since OIL data is NOT provided, the system shouldn't even reach the dataframe logic, 
    # but if we pass empty dataframes (simulating the failure in audit.py), it must block.
    import pandas as pd
    is_ready, msg, stats = validator.check_readiness(pd.DataFrame(columns=["well_id", "wellbore_id", "event_type"]), pd.DataFrame(columns=["well_id", "wellbore_id", "md"]))
    
    assert is_ready is False
    assert "Minimum 5 required" in msg

def test_geospatial_refusal():
    """
    Verifies that the geospatial layer calculates distance with coordinates and refuses when well is unknown.
    """
    geo = GeospatialIntelligence()
    assert geo.coordinates_available is True
    
    # Active well 15/9-F-15 returns nearby wells sorted by Haversine distance
    nearby = geo.find_nearby_wells("15/9-F-15", radius_km=5.0)
    assert len(nearby) > 0
    assert nearby[0]["distance_km"] <= 5.0
    
    # Unknown well ID returns empty list per missing data policy
    unknown_nearby = geo.find_nearby_wells("UNKNOWN_WELL_999", radius_km=5.0)
    assert unknown_nearby == []
