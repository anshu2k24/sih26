#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from ertmac.ml.ingestion import IngestionValidator

def main():
    validator = IngestionValidator()
    
    events_path = REPO_ROOT / "data" / "raw" / "oil_ertmac_events.parquet"
    sensors_path = REPO_ROOT / "data" / "raw" / "oil_ertmac_sensors.parquet"
    
    if not events_path.exists() or not sensors_path.exists():
        print("ML BLOCKED — NEED REAL DATA")
        print("\nReason: OIL/eRTMAC datasets not found in data/raw/.")
        sys.exit(0)
        
    df_events = pd.read_parquet(events_path)
    df_sensors = pd.read_parquet(sensors_path)
    
    try:
        is_ready, msg = validator.check_readiness(df_events, df_sensors)
        if is_ready:
            print("READY FOR FIRST ML EXPERIMENT")
        else:
            print("ML BLOCKED — NEED REAL DATA")
            print(f"\nReason: {msg}")
    except Exception as e:
        print("ML BLOCKED — NEED REAL DATA")
        print(f"\nReason: Ingestion error - {str(e)}")

if __name__ == "__main__":
    main()
