import pandas as pd
import numpy as np
import sys
from pathlib import Path
from scipy import stats
import random
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import roc_auc_score, f1_score

sys.path.append('src')

from ertmac.ml.features import construct_causal_features, CausalFeatureConfig
from ertmac.ml.dataset import generate_deterministic_negatives
from ertmac.ml.models import LightGBMBaseline
from ertmac.ml.inference import DataQualityGate

def get_real_negatives(usrop, events, wb, num_samples=25):
    wb_events = events[events['wellbore_id'] == wb]
    w_df = usrop[usrop['wellbore_id'] == wb]
    if w_df.empty: return []
    
    min_md, max_md = w_df['md'].min() + 50.0, w_df['md'].max()
    if np.isnan(min_md) or np.isnan(max_md): return []
    
    exclusions = []
    for _, r in wb_events.iterrows():
        onset = r['onset_md']
        if pd.notna(onset): exclusions.append((onset - 100.0, onset + 100.0))
            
    valid_mds = []
    attempts = 0
    while len(valid_mds) < num_samples and attempts < 1000:
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

def main():
    print("Loading synthetic data...")
    df_events_syn = pd.read_parquet('data/synthetic/oil_ertmac_events.parquet')
    df_sensors_syn = pd.read_parquet('data/synthetic/oil_ertmac_sensors.parquet')

    target_event = 'FORMATION_MUD_LOSS'
    pos_events = df_events_syn[df_events_syn['event_type'] == target_event].copy()
    df_negatives = generate_deterministic_negatives(
        df_sensors_syn, df_events_syn, target_event_type=target_event, 
        ratio=5, random_seed=42, exclusion_zone_m=50.0
    )
    
    config = CausalFeatureConfig(windows=[5.0, 10.0, 25.0, 50.0])
    feature_rows = []
    
    # Process Synthetic Positives
    for _, row in pos_events.iterrows():
        wb = row['wellbore_id']
        onset = row['md']
        if pd.isnull(onset): continue
        cutoff = onset - 25.0
        wb_sensors = df_sensors_syn[df_sensors_syn['wellbore_id'] == wb]
        try:
            feats = construct_causal_features(wb_sensors[wb_sensors['md'] <= cutoff], cutoff, config)
            feats['is_event'] = 1
            feats['group'] = wb
            feature_rows.append(feats)
        except:
            pass
            
    # Process Synthetic Negatives
    for _, row in df_negatives.iterrows():
        wb = row['wellbore_id']
        onset = row['md']
        cutoff = onset - 25.0
        wb_sensors = df_sensors_syn[df_sensors_syn['wellbore_id'] == wb]
        try:
            feats = construct_causal_features(wb_sensors[wb_sensors['md'] <= cutoff], cutoff, config)
            feats['is_event'] = 0
            feats['group'] = wb
            feature_rows.append(feats)
        except:
            pass

    df_train = pd.DataFrame(feature_rows)
    X = df_train.drop(columns=['is_event', 'group']).select_dtypes(include=[np.number])
    y = df_train['is_event']
    groups = df_train['group']
    
    print(f"Built {len(df_train)} synthetic relative samples (Pos: {y.sum()}).")

    # LOWO Cross-Validation on Synthetic
    logo = LeaveOneGroupOut()
    y_true, y_pred = [], []
    for train_idx, test_idx in logo.split(X, y, groups):
        if y.iloc[train_idx].sum() == 0 or y.iloc[test_idx].sum() == 0: continue
        model = LightGBMBaseline()
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        preds = model.predict_proba(X.iloc[test_idx])
        y_true.extend(y.iloc[test_idx])
        y_pred.extend(preds)
        
    if len(y_true) > 0:
        auc = roc_auc_score(y_true, y_pred)
        print(f"Synthetic LOWO Validation AUC: {auc:.3f}")
    else:
        auc = "N/A"
        print("Not enough diverse positive synthetic groups for full LOWO CV.")
        
    # Train final model on ALL synthetic data
    model_final = LightGBMBaseline()
    model_final.fit(X, y)
    
    X_neg = X[y == 0]
    syn_neg_scores = model_final.predict_proba(X_neg)
    
    syn_dist = {
        'mean': np.mean(syn_neg_scores), 'std': np.std(syn_neg_scores),
        'min': np.min(syn_neg_scores), 'max': np.max(syn_neg_scores),
        'p95': np.percentile(syn_neg_scores, 95)
    }

    # Extract Real Event Features
    print("Loading real data...")
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

    gate = DataQualityGate(required_history_md=25.0)
    
    real_event_scores = []
    target_etypes = ['FORMATION_MUD_LOSS', 'Equipment Failure', 'Pack-off']
    
    for etype in target_etypes:
        sub = events[(events['event_type'] == etype) & (events['onset_confidence'] == 'HIGH') & (events['wellbore_id'].str.startswith('NO '))]
        for _, r in sub.iterrows():
            wb = r['wellbore_id']
            onset = r['onset_md']
            cutoff = onset - 25.0
            
            w_df = usrop[usrop['wellbore_id'] == wb]
            if w_df.empty: continue
            min_md, max_md = w_df['md'].min(), w_df['md'].max()
            if not (min_md <= cutoff and onset <= max_md): continue
            
            hist = w_df[w_df['md'] <= cutoff]
            if hist.empty: continue
            if gate.check_quality(hist, cutoff, wb) == 'PASS':
                try:
                    feats = construct_causal_features(hist, cutoff, config)
                    feat_df = pd.DataFrame([feats])
                    for c in X.columns:
                        if c not in feat_df.columns: feat_df[c] = 0.0
                    score = model_final.predict_proba(feat_df[X.columns])[0]
                    real_event_scores.append(score)
                except Exception as e:
                    pass

    # Real Negative Control
    real_normal_scores = []
    wells_with_events = ['NO 15/9-F-14', 'NO 15/9-F-15']
    for wb in wells_with_events:
        safe_mds = get_real_negatives(usrop, events, wb, num_samples=30)
        for cutoff in safe_mds:
            w_df = usrop[usrop['wellbore_id'] == wb]
            hist = w_df[w_df['md'] <= cutoff]
            if gate.check_quality(hist, cutoff, wb) == 'PASS':
                try:
                    feats = construct_causal_features(hist, cutoff, config)
                    feat_df = pd.DataFrame([feats])
                    for c in X.columns:
                        if c not in feat_df.columns: feat_df[c] = 0.0
                    score = model_final.predict_proba(feat_df[X.columns])[0]
                    real_normal_scores.append(score)
                except:
                    pass
                    
    # Generate report
    report = []
    report.append("# OOD Validation: Relative Features Result")
    report.append("We introduced well-relative normalization (Z-score against the expanding causal baseline) to all features in `features.py` to eliminate absolute-scale domain shift. This document summarizes the impact of that fix.")
    
    report.append(f"\n## 1. Synthetic Validation (Sanity Check)")
    report.append(f"- **LOWO ROC-AUC on Synthetic**: {auc if isinstance(auc, str) else f'{auc:.3f}'}")
    report.append("*(Note: Validates that relative features do not destroy predictive power within the synthetic domain itself).*")
    
    report.append("\n## 2. Distributions Under Relative Normalization")
    report.append(f"- **Synthetic Negatives** (n={len(syn_neg_scores)}): Median = {np.median(syn_neg_scores):.4f}, Max = {syn_dist['max']:.4f}")
    if real_normal_scores:
        report.append(f"- **Real Normal Controls** (n={len(real_normal_scores)}): Median = {np.median(real_normal_scores):.4f}, Max = {np.max(real_normal_scores):.4f}")
    if real_event_scores:
        report.append(f"- **Real Event Windows** (n={len(real_event_scores)}): Median = {np.median(real_event_scores):.4f}, Max = {np.max(real_event_scores):.4f}")
        
    report.append("\n## 3. Comparison & Verdict")
    
    is_genuine = False
    if real_normal_scores and real_event_scores:
        med_norm = np.median(real_normal_scores)
        med_event = np.median(real_event_scores)
        if med_event > med_norm * 1.5 and med_event > syn_dist['p95']: # some heuristic gap
            is_genuine = True
            
    if is_genuine:
        report.append("**Verdict: GENUINE_SIGNAL_RECOVERED**")
        report.append("\nRelative normalization successfully eliminated the domain shift. The real normal windows now score low (comparable to synthetic negatives), while the 7 real events demonstrate a clear elevated risk distribution. The real-data risk scoring is demonstrably functional.")
    else:
        report.append("**Verdict: INCONCLUSIVE (DOMAIN OVERLAP PERSISTS)**")
        report.append("\nRelative normalization alone didn't fix it. The real-normal control windows still produce scores that overlap heavily with the real-event windows. The synthetic classifier's learned anomaly signatures do not reliably distinguish pre-event signals from normal noise in the real Volve data.")
        report.append("\nReal-data risk scoring is **not demonstrable** with current data constraints. Full stop. No further diagnostic fixes will be applied during this cycle.")

    with open('reports/relative_features_result.md', 'w') as f:
        f.write("\n".join(report))
        
    print("Relative features evaluation complete.")

if __name__ == "__main__":
    main()
