#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from ertmac.ml.synthetic_evaluation import evaluate_quality

def main():
    syn_dir = REPO_ROOT / "data" / "synthetic"
    events_path = syn_dir / "oil_ertmac_events.parquet"
    sensors_path = syn_dir / "oil_ertmac_sensors.parquet"
    
    if not events_path.exists() or not sensors_path.exists():
        print("Synthetic data not found.")
        sys.exit(1)
        
    df_events = pd.read_parquet(events_path)
    df_sensors = pd.read_parquet(sensors_path)
    
    df_scores, total_score = evaluate_quality(df_events, df_sensors)
    
    out_dir = REPO_ROOT / "reports" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    df_scores.to_csv(out_dir / "synthetic_quality_score.csv", index=False)
    
    # Feature Distributions
    numeric_cols = ["rop", "wob", "rpm", "torque", "hookload", "spp", "flow_in", "mud_density"]
    df_dist = df_sensors[numeric_cols].describe().T
    df_dist.to_csv(out_dir / "synthetic_feature_distribution_summary.csv")
    
    fig_dir = REPO_ROOT / "reports" / "figures" / "synthetic_quality"
    fig_dir.mkdir(parents=True, exist_ok=True)
    
    print("=== Synthetic Data Quality Score ===")
    print(df_scores.to_string(index=False))
    print(f"\nOverall Score: {total_score}/100.0")
    
    if total_score < 100:
        print("\n[FLAG] Synthetic behavior is visibly artificial in some components (e.g. perfect linear ramps causing 1.0 AUC, or lack of cross-channel physics).")

if __name__ == "__main__":
    main()
