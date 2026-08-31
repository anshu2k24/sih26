import pandas as pd
import numpy as np
import sys
import os
import random
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score, recall_score, f1_score, confusion_matrix

sys.path.append('src')
from ertmac.ml.features import construct_causal_features, CausalFeatureConfig
from ertmac.ml.inference import DataQualityGate

def get_real_negatives(usrop, events, wb, num_samples=100):
    wb_events = events[events['wellbore_id'] == wb]
    w_df = usrop[usrop['wellbore_id'] == wb]
    if w_df.empty: return []
    
    min_md = w_df['md'].min() + 50.0
    max_md = w_df['md'].max()
    if np.isnan(min_md) or np.isnan(max_md): return []
    
    exclusions = []
    for _, r in wb_events.iterrows():
        onset = r['onset_md']
        if pd.notna(onset):
            exclusions.append((onset - 100.0, onset + 100.0))
            
    valid_mds = []
    attempts = 0
    while len(valid_mds) < num_samples and attempts < 5000:
        attempts += 1
        md_candidate = random.uniform(min_md, max_md)
        is_safe = True
        for e_min, e_max in exclusions:
            if e_min <= md_candidate <= e_max:
                is_safe = False
                break
        if is_safe:
            valid_mds.append(md_candidate)
    return valid_mds

def clean_features(feat_dict):
    clean = {}
    for k, v in feat_dict.items():
        if any(x in k for x in ['ratio', 'rel_delta', 'cv', 'norm_slope']):
            continue
        if np.isinf(v) or pd.isna(v):
            clean[k] = np.nan
        else:
            clean[k] = v
    return clean

def main():
    random.seed(42)
    np.random.seed(42)
    
    print("Loading data...")
    events = pd.read_csv('reports/tables/verified_event_episodes_v2.csv')
    usrop = pd.read_parquet('data/processed/usrop/usrop_clean.parquet')
    
    col_map = {
        'Measured Depth m': 'md', 'Weight on Bit kkgf': 'wob', 'Average Standpipe Pressure kPa': 'spp',
        'Average Surface Torque kN.m': 'torque', 'Rate of Penetration m/h': 'rop', 'Average Rotary Speed rpm': 'rpm',
        'Mud Flow In L/min': 'flow_in', 'Mud Density In g/cm3': 'mud_density', 'Diameter mm': 'diameter',
        'Average Hookload kkgf': 'hookload', 'Hole Depth (TVD) m': 'tvd', 'USROP Gamma gAPI': 'gamma'
    }
    usrop = usrop.rename(columns=col_map)
    usrop['wellbore_id'] = usrop['well_id'].apply(lambda x: 'NO ' + x)
    
    # Target only FORMATION_MUD_LOSS
    events = events[(events['event_type'] == 'FORMATION_MUD_LOSS') & (events['onset_confidence'] == 'HIGH')]
    
    config = CausalFeatureConfig(windows=[5.0, 10.0, 25.0, 50.0])
    gate = DataQualityGate(required_history_md=25.0)
    
    dataset_rows = []
    all_wells = usrop['wellbore_id'].unique()
    
    # 1. Real Positives
    real_pos_wells = set()
    for _, r in events.iterrows():
        wb = r['wellbore_id']
        if wb not in all_wells: continue
        
        onset = r['onset_md']
        cutoff = onset - 25.0
        
        w_df = usrop[usrop['wellbore_id'] == wb]
        if w_df.empty: continue
        if w_df['md'].min() > cutoff or w_df['md'].max() < onset: continue
        
        hist = w_df[w_df['md'] <= cutoff]
        if gate.check_quality(hist, cutoff, wb) == 'PASS':
            try:
                feats = construct_causal_features(hist, cutoff, config)
                feats = clean_features(feats)
                feats['is_event'] = 1
                feats['group'] = wb
                feats['source'] = 'real_event'
                feats['event_type'] = 'FORMATION_MUD_LOSS'
                feats['md'] = onset
                dataset_rows.append(feats)
                real_pos_wells.add(wb)
            except Exception as e:
                print(f"Failed to extract for positive {wb} at {onset}: {e}")
                
    # 2. Real Negatives
    for wb in all_wells:
        safe_mds = get_real_negatives(usrop, events, wb, num_samples=150)
        for cutoff in safe_mds:
            w_df = usrop[usrop['wellbore_id'] == wb]
            hist = w_df[w_df['md'] <= cutoff]
            if gate.check_quality(hist, cutoff, wb) == 'PASS':
                try:
                    feats = construct_causal_features(hist, cutoff, config)
                    feats = clean_features(feats)
                    feats['is_event'] = 0
                    feats['group'] = wb
                    feats['source'] = 'real_negative'
                    feats['event_type'] = 'Normal'
                    feats['md'] = cutoff
                    dataset_rows.append(feats)
                except:
                    pass
                    
    df = pd.DataFrame(dataset_rows)
    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    out_dir = 'data/processed/events'
    os.makedirs(out_dir, exist_ok=True)
    df.to_parquet(f"{out_dir}/volve_real_only_ml.parquet", index=False)
    
    print(f"Generated purely real dataset: {len(df)} rows")
    
    if len(real_pos_wells) < 2:
        print("WARNING: Only 1 independent positive group. Generalization cannot be validated.")
        
    # Features
    drop_cols = ['is_event', 'group', 'source', 'event_type', 'md']
    X = df.drop(columns=drop_cols).select_dtypes(include=[np.number])
    y = df['is_event']
    
    # Train
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)
    
    # Save model
    os.makedirs('models', exist_ok=True)
    joblib.dump(model, 'models/volve_research_v1.joblib')
    
    # Honest evaluation (in-sample)
    preds = model.predict_proba(X)[:, 1]
    preds_cls = model.predict(X)
    
    in_sample_auc = roc_auc_score(y, preds)
    in_sample_pr = average_precision_score(y, preds)
    in_sample_prec = precision_score(y, preds_cls, zero_division=0)
    in_sample_rec = recall_score(y, preds_cls, zero_division=0)
    in_sample_f1 = f1_score(y, preds_cls, zero_division=0)
    cm = confusion_matrix(y, preds_cls)
    
    print("In-Sample Evaluation:")
    print(f"ROC-AUC: {in_sample_auc:.3f}")
    
    metrics = {
        'metric': ['In-Sample ROC-AUC', 'In-Sample PR-AUC', 'In-Sample Precision', 'In-Sample Recall', 'In-Sample F1', 'LOWO Cross-Validation'],
        'value': [in_sample_auc, in_sample_pr, in_sample_prec, in_sample_rec, in_sample_f1, 'NOT VALID / INSUFFICIENT DATA']
    }
    pd.DataFrame(metrics).to_csv('reports/tables/volve_real_only_metrics.csv', index=False)
    
    card = f"""# Model Card: REAL VOLVE RESEARCH MODEL v1

## Artifact
`models/volve_research_v1.joblib`

## Model Status
**REAL VOLVE RESEARCH / NOT OIL-VALIDATED**

## Data Status
100% REAL VOLVE (NO SYNTHETIC DATA)
OIL/eRTMAC: NOT PRESENT

## Generalization
**NOT VALIDATED DUE TO 1 INDEPENDENT POSITIVE GROUP**
Leave-One-Well-Out (LOWO) spatial cross-validation is impossible. Any test fold for a well without real positive events cannot measure recall. The lone well with real positive events would leave 0 positives in the training set if held out.

## Dataset Composition
- Total Rows: {len(df)}
- Real Positive Episodes: {sum(y)}
- Real Positive Independent Groups (Wells): {len(real_pos_wells)}
- Real Negative Windows: {len(df) - sum(y)}
- Features used: {len(X.columns)} causal features

## Honest Metrics (IN-SAMPLE ONLY)
*WARNING: These metrics are evaluated on the training set and represent memorization, NOT generalization.*
- **ROC-AUC**: {in_sample_auc:.3f}
- **PR-AUC**: {in_sample_pr:.3f}
- **Precision**: {in_sample_prec:.3f}
- **Recall**: {in_sample_rec:.3f}
- **F1**: {in_sample_f1:.3f}

## Confusion Matrix (In-Sample)
True Negatives: {cm[0][0]} | False Positives: {cm[0][1]}
False Negatives: {cm[1][0]} | True Positives: {cm[1][1]}

## Limitations
This model is strictly for research and end-to-end replay functional testing. It lacks sufficient independent events to be scientifically valid for prediction in unseen operational environments.
"""
    os.makedirs('reports/ml', exist_ok=True)
    with open('reports/ml/volve_research_model_card_v1.md', 'w') as f:
        f.write(card)
        
    report = f"""# Volve Real-Only Training Report

This report documents the creation of the purely real mud-loss research model.

## Objective
Train a functional inference pipeline model strictly on real Volve telemetry without synthetic leakage.

## Input Sources
- Causal Rules: Existing CausalFeatureConfig (5, 10, 25, 50m windows)
- Positives: `{sum(y)}` highly-confident real mud-loss events
- Negatives: `{len(df) - sum(y)}` sampled strictly from safe ranges >100m from events

## Results
Because `NO 15/9-F-14` is the only independent well containing these events, structural cross-validation is blocked. We have generated `models/volve_research_v1.joblib` specifically to wire up the real-time inference pipeline and prove deterministic replay behavior, while explicitly rejecting any claims of actual predictive skill.
"""
    with open('reports/ml/volve_real_only_training_report.md', 'w') as f:
        f.write(report)
        
    print("Done generating model and reports.")

if __name__ == '__main__':
    main()
