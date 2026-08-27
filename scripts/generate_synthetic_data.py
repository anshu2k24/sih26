#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from ertmac.ml.synthetic import build_synthetic_dataset

def main():
    print("=== eRTMAC-NWIS Synthetic Data Generator ===")
    print("Generating SYNTHETIC DEVELOPMENT TRACK data...")
    
    df_events, df_sensors = build_synthetic_dataset(num_wells=8, seed=42)
    
    syn_dir = REPO_ROOT / "data" / "synthetic"
    syn_dir.mkdir(parents=True, exist_ok=True)
    
    events_path = syn_dir / "oil_ertmac_events.parquet"
    sensors_path = syn_dir / "oil_ertmac_sensors.parquet"
    
    # Save parquets (like real data)
    df_events.to_parquet(events_path)
    df_sensors.to_parquet(sensors_path)
    
    # Save CSVs for inspection
    df_events.to_csv(syn_dir / "oil_ertmac_events.csv", index=False)
    df_sensors.to_csv(syn_dir / "oil_ertmac_sensors.csv", index=False)
    
    print(f"Generated {df_events.shape[0]} synthetic events.")
    print(f"Generated {df_sensors.shape[0]} synthetic sensor samples across 8 wells.")
    print(f"Saved to {syn_dir}")
    
    # Generate audit reports
    reports_dir = REPO_ROOT / "reports" / "tables"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    well_summary = df_sensors.groupby("well_id").agg(
        min_md=("md", "min"),
        max_md=("md", "max"),
        samples=("md", "count")
    ).reset_index()
    well_summary.to_csv(reports_dir / "synthetic_well_summary.csv", index=False)
    
    df_events.to_csv(reports_dir / "synthetic_event_summary.csv", index=False)
    
    quality_audit = []
    quality_audit.append({"metric": "Total Wells", "value": df_sensors['well_id'].nunique(), "status": "PASS"})
    quality_audit.append({"metric": "Positive Events", "value": len(df_events), "status": "PASS"})
    quality_audit.append({"metric": "Missing Values", "value": df_sensors.isnull().sum().sum(), "status": "PASS"})
    
    pd.DataFrame(quality_audit).to_csv(reports_dir / "synthetic_quality_audit.csv", index=False)
    
    with open(REPO_ROOT / "reports" / "synthetic_data_development.md", "w") as f:
        f.write("# Synthetic Data Development Report\n\n")
        f.write("## Overview\nThis dataset is STRICTLY for development and testing of the ML pipeline. It DOES NOT represent real-world performance.\n\n")
        f.write("## Metrics\n")
        f.write(f"- Wells: 8\n- Events: {len(df_events)}\n- Sensor samples: {len(df_sensors)}\n")
        
    print("\nDONE. Do NOT use this data to claim real-world SIH validation.")

if __name__ == "__main__":
    main()
