#!/usr/bin/env python3
import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from ertmac.ml.ingestion import IngestionValidator
from ertmac.ml.dataset import generate_deterministic_negatives
from ertmac.ml.features import construct_causal_features, CausalFeatureConfig
from ertmac.ml.pipeline import LOWOExperimentRunner
from ertmac.ml.contracts import MLPipelineConfig
from ertmac.ml.models import PersistenceBaseline, LogisticRegressionBaseline, LightGBMBaseline

def build_dataset(df_events, df_sensors, target_event='FORMATION_MUD_LOSS', horizon=25.0):
    pos_events = df_events[df_events['event_type'] == target_event].copy()
    
    # Generate negatives
    df_negatives = generate_deterministic_negatives(
        df_sensors, df_events, target_event_type=target_event, 
        ratio=5, random_seed=42, exclusion_zone_m=50.0
    )
    
    feature_rows = []
    config = CausalFeatureConfig(windows=[5.0, 10.0, 25.0])
    
    # Process Positives
    for _, row in pos_events.iterrows():
        wb = row['wellbore_id']
        onset = row['md']
        group = row['independent_well_group']
        
        if pd.isnull(onset): continue
        cutoff = onset - horizon
        
        wb_sensors = df_sensors[df_sensors['wellbore_id'] == wb]
        try:
            feats = construct_causal_features(wb_sensors, cutoff, config)
            feats['well_id'] = row['well_id']
            feats['wellbore_id'] = wb
            feats['independent_group'] = group
            feats['is_event'] = 1
            feature_rows.append(feats)
        except ValueError:
            pass # No history before cutoff or gap too large
            
    # Process Negatives
    # Negatives have their 'md' as the pseudo-onset
    if not df_negatives.empty:
        for _, row in df_negatives.iterrows():
            wb = row['wellbore_id']
            onset = row['md']
            group = df_events[df_events['wellbore_id'] == wb]['independent_well_group'].iloc[0] if wb in df_events['wellbore_id'].values else wb
            
            cutoff = onset - horizon
            wb_sensors = df_sensors[df_sensors['wellbore_id'] == wb]
            try:
                feats = construct_causal_features(wb_sensors, cutoff, config)
                feats['well_id'] = row['well_id']
                feats['wellbore_id'] = wb
                feats['independent_group'] = group
                feats['is_event'] = 0
                feature_rows.append(feats)
            except ValueError:
                pass
                
    if not feature_rows:
        return pd.DataFrame()
        
    return pd.DataFrame(feature_rows)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["real", "synthetic"], default="real")
    args = parser.parse_args()
    
    if args.dataset == "real":
        processed_dir = REPO_ROOT / "data" / "processed"
    else:
        processed_dir = REPO_ROOT / "data" / "synthetic"
        print("🚨 WARNING: SYNTHETIC DEVELOPMENT MODE 🚨")
        print("SYNTHETIC DEVELOPMENT ONLY — NOT REAL-WORLD PERFORMANCE")
        
    events_path = processed_dir / ("oil_ertmac_events.parquet" if args.dataset == "synthetic" else "normalized_events.parquet")
    sensors_path = processed_dir / ("oil_ertmac_sensors.parquet" if args.dataset == "synthetic" else "normalized_sensors.parquet")
    
    if not events_path.exists() or not sensors_path.exists():
        print("ML BLOCKED — NEED REAL DATA (Processed files missing)")
        sys.exit(0)
        
    df_events = pd.read_parquet(events_path)
    df_sensors = pd.read_parquet(sensors_path)
    
    # In synthetic mode, we must run ingestion validation manually because they were written straight to parquet
    from ertmac.ml.normalization import handle_sentinels_and_impossible
    if args.dataset == "synthetic":
        df_events, _ = handle_sentinels_and_impossible(df_events, is_sensor=False)
        df_sensors, _ = handle_sentinels_and_impossible(df_sensors, is_sensor=True)
    
    validator = IngestionValidator()
    is_ready, msg, stats = validator.check_readiness(df_events, df_sensors)
    
    if not is_ready:
        print(f"ML BLOCKED — NEED REAL DATA\nReason: {msg}")
        sys.exit(0)
        
    print("Readiness Gate PASSED. Building Dataset...")
    df_features = build_dataset(df_events, df_sensors)
    
    if df_features.empty or df_features['is_event'].nunique() < 2:
        print("ML BLOCKED — NEED REAL DATA\nReason: Insufficient samples after feature engineering.")
        sys.exit(0)
        
    # Run Experiment
    config = MLPipelineConfig(min_independent_positive_well_groups=5)
    runner = LOWOExperimentRunner(config)
    
    models = {
        "Persistence": PersistenceBaseline(),
        "LogisticRegression": LogisticRegressionBaseline(),
        "LightGBM": LightGBMBaseline()
    }
    
    all_macros = []
    
    reports_dir = REPO_ROOT / "reports" / "ml"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    for name, model in models.items():
        print(f"Training {name}...")
        res = runner.run_experiment(df_features, model)
        
        macro = res['macro_metrics']
        macro['Model'] = name
        all_macros.append(macro)
        
        # Save predictions
        preds = res.get('predictions')
        if preds is not None:
            preds.to_csv(reports_dir / f"{name}_predictions.csv", index=False)
            
        # Save feature importance if LightGBM
        fi = res.get('feature_importances')
        if fi:
            pd.DataFrame(list(fi.items()), columns=['Feature', 'Importance']).to_csv(reports_dir / "feature_importance.csv", index=False)
            
    df_comp = pd.DataFrame(all_macros)
    df_comp.to_csv(reports_dir / "model_comparison.csv", index=False)
    
    print("\nExperiment Complete. Results saved to reports/ml/.")
    print(df_comp)

if __name__ == "__main__":
    main()
