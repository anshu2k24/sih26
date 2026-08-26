#!/usr/bin/env python3
import os
import pandas as pd
from pathlib import Path
import json

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys_path = str(REPO_ROOT / "src")
import sys
if sys_path not in sys.path:
    sys.path.append(sys_path)
    
from ertmac.ml.ingestion import IngestionValidator

REPORTS_DIR = REPO_ROOT / "reports"
TABLES_DIR = REPORTS_DIR / "tables"

def main():
    validator = IngestionValidator()
    
    # Check if files exist
    events_path = REPO_ROOT / "data" / "raw" / "oil_ertmac_events.parquet"
    sensors_path = REPO_ROOT / "data" / "raw" / "oil_ertmac_sensors.parquet"
    
    status = "BLOCKED"
    reason = ""
    
    if not events_path.exists() or not sensors_path.exists():
        reason = "OIL/eRTMAC datasets not found in data/raw/. (Missing oil_ertmac_events.parquet or oil_ertmac_sensors.parquet)"
        # We write dummy empty tables to satisfy the request
        pd.DataFrame(columns=["metric", "value"]).to_csv(TABLES_DIR / "oil_event_coverage.csv", index=False)
        pd.DataFrame(columns=["metric", "value"]).to_csv(TABLES_DIR / "oil_sensor_coverage.csv", index=False)
        pd.DataFrame(columns=["metric", "value"]).to_csv(TABLES_DIR / "oil_well_mapping.csv", index=False)
        pd.DataFrame(columns=["metric", "value"]).to_csv(TABLES_DIR / "oil_data_quality.csv", index=False)
        
    else:
        # Load and validate
        df_events = pd.read_parquet(events_path)
        df_sensors = pd.read_parquet(sensors_path)
        
        try:
            evt_rep = validator.validate_event_data(df_events)
            sens_rep = validator.validate_sensor_data(df_sensors)
            
            is_ready, msg = validator.check_readiness(df_events, df_sensors)
            if is_ready:
                status = "READY_FOR_FIRST_ML_EXPERIMENT"
                reason = "All ingestion validations and coverage checks passed."
            else:
                reason = msg
                
        except Exception as e:
            reason = f"Ingestion validation failed: {str(e)}"
            
    # Write audit report
    audit_md = f"""# OIL/eRTMAC Data Ingestion Audit

## Dataset Inspected
- Expected Events: `data/raw/oil_ertmac_events.parquet`
- Expected Sensors: `data/raw/oil_ertmac_sensors.parquet`

## Current ML Status
**{status}**

### Reason
{reason}

### Readiness Requirements
To pass the scientific gate, the dataset must satisfy:
1. `FORMATION_MUD_LOSS` onset MD is available.
2. Contains `>=5` verified positive wells.
3. Telemetry strictly overlaps positive event wells.
4. Telemetry history reaches at least `onset_md - 25m` for `>=5` positive wells.
5. No impossible/non-monotonic depth joins.
6. Clean timestamps and MD synchronization.

*(No ML model has been trained. The Volve dataset was explicitly NOT substituted.)*
"""
    with open(REPORTS_DIR / "oil_ertmac_ingestion_audit.md", "w") as f:
        f.write(audit_md)
        
    # Append to readiness report
    readiness_path = REPORTS_DIR / "ml_pipeline_readiness.md"
    if readiness_path.exists():
        with open(readiness_path, "a") as f:
            f.write(f"\n## LATEST INGESTION AUDIT RESULT\nStatus: **{status}**\nReason: {reason}\n")
            
if __name__ == "__main__":
    main()
