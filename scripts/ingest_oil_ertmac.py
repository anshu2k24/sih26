#!/usr/bin/env python3
import sys
import json
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from ertmac.ml.normalization import ingest_file
from ertmac.ml.ingestion import IngestionValidator

def main():
    raw_dir = REPO_ROOT / "data" / "raw"
    processed_dir = REPO_ROOT / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    print("=== eRTMAC-NWIS Data Ingestion & Audit ===")
    
    # 1. Discover files
    event_files = list(raw_dir.glob("*event*.*")) + list(raw_dir.glob("*ddr*.*"))
    sensor_files = list(raw_dir.glob("*sensor*.*")) + list(raw_dir.glob("*witsml*.*"))
    
    if not event_files and not sensor_files:
        print("ML BLOCKED — NEED REAL DATA")
        print("\nReason: No candidate files found in data/raw/.")
        sys.exit(0)
        
    print(f"Found {len(event_files)} event candidate files and {len(sensor_files)} sensor candidate files.")
    
    # 2. Ingest and Normalize
    df_events = []
    invalid_summaries = []
    for f in event_files:
        try:
            df, invalid_rep = ingest_file(f, is_event=True)
            df_events.append(df)
            invalid_rep["file"] = f.name
            invalid_summaries.append(invalid_rep)
            print(f"[OK] Ingested event file: {f.name}")
        except Exception as e:
            print(f"[ERROR] Failed to ingest {f.name}: {e}")
            
    df_sensors = []
    for f in sensor_files:
        try:
            df, invalid_rep = ingest_file(f, is_event=False)
            df_sensors.append(df)
            invalid_rep["file"] = f.name
            invalid_summaries.append(invalid_rep)
            print(f"[OK] Ingested sensor file: {f.name}")
        except Exception as e:
            print(f"[ERROR] Failed to ingest {f.name}: {e}")
            
    # Instead of exiting early, create empty dataframes if needed to generate reports
    from ertmac.ml.normalization import CANONICAL_EVENTS, CANONICAL_SENSORS
    df_event_all = pd.concat(df_events, ignore_index=True) if df_events else pd.DataFrame(columns=CANONICAL_EVENTS)
    df_sensor_all = pd.concat(df_sensors, ignore_index=True) if df_sensors else pd.DataFrame(columns=CANONICAL_SENSORS + ["wellbore_id"])
    
    # Write normalized processed files (never modifying raw)
    out_events = processed_dir / "normalized_events.parquet"
    out_sensors = processed_dir / "normalized_sensors.parquet"
    
    if df_events:
        df_event_all.to_parquet(out_events)
        print(f"Wrote normalized events to {out_events}")
    if df_sensors:
        df_sensor_all.to_parquet(out_sensors)
        print(f"Wrote normalized sensors to {out_sensors}")
    
    # Write invalid report
    if invalid_summaries:
        df_invalid = pd.DataFrame(invalid_summaries).fillna(0)
        invalid_out = REPO_ROOT / "reports" / "tables" / "ingestion_invalid_values.csv"
        invalid_out.parent.mkdir(parents=True, exist_ok=True)
        df_invalid.to_csv(invalid_out, index=False)
        print(f"Wrote invalid value audit to {invalid_out}")
    
    # Load explicit mappings if provided
    mappings_file = raw_dir / "well_mappings.json"
    explicit_mappings = {}
    if mappings_file.exists():
        with open(mappings_file, 'r') as f:
            explicit_mappings = json.load(f)
            
    # 3. Validate
    validator = IngestionValidator(explicit_mappings=explicit_mappings)
    
    event_report = validator.validate_event_data(df_event_all)
    sensor_report = validator.validate_sensor_data(df_sensor_all)
    
    print("\n--- Event Report ---")
    for k, v in event_report.items(): print(f"{k}: {v}")
    
    print("\n--- Sensor Report ---")
    for k, v in sensor_report.items(): print(f"{k}: {v}")
    
    # Save quality and coverage reports
    pd.DataFrame([event_report, sensor_report]).to_csv(REPO_ROOT / "reports" / "tables" / "ingestion_quality_summary.csv", index=False)
    
    # 4. Readiness Gate
    is_ready, msg, stats = validator.check_readiness(df_event_all, df_sensor_all)
    pd.DataFrame([stats]).to_csv(REPO_ROOT / "reports" / "tables" / "ingestion_sensor_coverage.csv", index=False)
    
    print("\n--- ML Readiness Gate ---")
    for k, v in stats.items(): print(f"{k}: {v}")
    
    if is_ready:
        print(f"\n[PASS] READY FOR FIRST ML EXPERIMENT")
    else:
        print(f"\n[FAIL] ML BLOCKED — NEED REAL DATA")
        print(f"Reason: {msg}")

if __name__ == "__main__":
    main()
