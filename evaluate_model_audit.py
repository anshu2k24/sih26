import pandas as pd
import numpy as np
import sys
import os
import random
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score, recall_score, f1_score
import joblib

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
    # setting seed for deterministic eval
    random.seed(42)
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

def perturb_series(df_hist, etype, cutoff):
    df = df_hist.copy()
    mask = (df['md'] >= cutoff - 25.0) & (df['md'] <= cutoff)
    
    if etype == 'FORMATION_MUD_LOSS':
        drop_factor = random.uniform(0.66, 0.85)
        if 'spp' in df.columns:
            noise = np.random.normal(0, 0.05 * df.loc[mask, 'spp'].mean(), size=mask.sum())
            df.loc[mask, 'spp'] = df.loc[mask, 'spp'] * drop_factor + noise
        if 'flow_in' in df.columns:
            df.loc[mask, 'flow_in'] = df.loc[mask, 'flow_in'] * drop_factor
            
    elif etype == 'Pack-off':
        surge_factor = random.uniform(1.20, 1.35)
        if 'spp' in df.columns:
            df.loc[mask, 'spp'] = df.loc[mask, 'spp'] * surge_factor
        if 'torque' in df.columns:
            volatility = np.random.normal(0, 0.20 * df.loc[mask, 'torque'].mean(), size=mask.sum())
            df.loc[mask, 'torque'] = df.loc[mask, 'torque'] + volatility
            
    elif etype == 'Equipment Failure':
        if 'rop' in df.columns:
            slowdown = np.linspace(1.0, random.uniform(0.2, 0.5), mask.sum())
            noise = np.random.normal(0, 0.1 * df.loc[mask, 'rop'].mean(), size=mask.sum())
            df.loc[mask, 'rop'] = df.loc[mask, 'rop'] * slowdown + noise
            
    return df

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

def build_eval_dataset():
    random.seed(42)
    np.random.seed(42)
    
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
    
    config = CausalFeatureConfig(windows=[5.0, 10.0, 25.0, 50.0])
    gate = DataQualityGate(required_history_md=25.0)
    
    dataset_rows = []
    target_etypes = ['FORMATION_MUD_LOSS', 'Equipment Failure', 'Pack-off']
    all_wells = usrop['wellbore_id'].unique()
    
    real_pos_wells = set()
    for etype in target_etypes:
        sub = events[(events['event_type'] == etype) & (events['onset_confidence'] == 'HIGH') & (events['wellbore_id'].str.startswith('NO '))]
        for _, r in sub.iterrows():
            wb = r['wellbore_id']
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
                    feats['event_type'] = etype
                    dataset_rows.append(feats)
                    real_pos_wells.add(wb)
                except Exception as e:
                    pass
                    
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
                    dataset_rows.append(feats)
                except:
                    pass
                    
    zero_pos_wells = [w for w in all_wells if w not in real_pos_wells]
    
    for wb in zero_pos_wells:
        anchors = get_real_negatives(usrop, events, wb, num_samples=30)
        idx = 0
        for etype in target_etypes:
            count = 0
            while count < 3 and idx < len(anchors):
                cutoff = anchors[idx]
                idx += 1
                w_df = usrop[usrop['wellbore_id'] == wb]
                hist = w_df[w_df['md'] <= cutoff]
                if gate.check_quality(hist, cutoff, wb) == 'PASS':
                    try:
                        p_hist = perturb_series(hist, etype, cutoff)
                        feats = construct_causal_features(p_hist, cutoff, config)
                        feats = clean_features(feats)
                        feats['is_event'] = 1
                        feats['group'] = wb
                        feats['source'] = 'synthetic_anchored_positive'
                        feats['event_type'] = etype
                        dataset_rows.append(feats)
                        count += 1
                    except Exception as e:
                        pass
    return pd.DataFrame(dataset_rows)

def evaluate():
    df = build_eval_dataset()
    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    model = joblib.load('models/ertmac_production_v1.joblib')
    
    X = df.drop(columns=['is_event', 'group', 'source', 'event_type']).select_dtypes(include=[np.number])
    # Align features just in case
    if hasattr(model, 'feature_names_in_'):
        X = X[model.feature_names_in_]
        
    y = df['is_event']
    groups = df['group']
    sources = df['source']
    
    logo = LeaveOneGroupOut()
    fold_metrics = []
    
    # 2. EXACT DATA LINEAGE
    total = len(df)
    real_pos = len(df[df['source'] == 'real_event'])
    real_neg = len(df[df['source'] == 'real_negative'])
    syn_pos = len(df[df['source'] == 'synthetic_anchored_positive'])
    num_wells = df['group'].nunique()
    
    print(f"Total samples: {total}")
    print(f"Real Positives: {real_pos}")
    print(f"Real Negatives: {real_neg}")
    print(f"Synthetic Positives: {syn_pos}")
    print(f"Total Groups (Wells): {num_wells}")
    
    # Create the tables
    lineage = df.groupby(['group', 'source']).size().reset_index(name='count')
    lineage.to_csv('reports/tables/current_model_lineage_audit.csv', index=False)
    
    lowo_res = []
    for train_idx, test_idx in logo.split(X, y, groups):
        test_group = groups.iloc[test_idx].iloc[0]
        test_sources = df.iloc[test_idx]['source'].value_counts().to_dict()
        train_sources = df.iloc[train_idx]['source'].value_counts().to_dict()
        lowo_res.append({
            'fold': test_group,
            'train_real_pos': train_sources.get('real_event', 0),
            'train_syn_pos': train_sources.get('synthetic_anchored_positive', 0),
            'train_real_neg': train_sources.get('real_negative', 0),
            'test_real_pos': test_sources.get('real_event', 0),
            'test_syn_pos': test_sources.get('synthetic_anchored_positive', 0),
            'test_real_neg': test_sources.get('real_negative', 0)
        })
    pd.DataFrame(lowo_res).to_csv('reports/tables/current_lowo_real_vs_synthetic.csv', index=False)
    
    # Evaluate ONLY on real data
    real_idx = df['source'].isin(['real_event', 'real_negative'])
    X_real = X[real_idx]
    y_real = y[real_idx]
    
    print("Real-only data evaluation:")
    print(f"Real data samples: {len(y_real)} (pos: {sum(y_real==1)}, neg: {sum(y_real==0)})")
    if len(np.unique(y_real)) > 1:
        preds = model.predict_proba(X_real)
        if preds.ndim == 2:
            preds = preds[:, 1]
        preds_cls = (preds > 0.5).astype(int)
        print("Pooled ROC-AUC:", roc_auc_score(y_real, preds))
        print("PR-AUC:", average_precision_score(y_real, preds))
        print("Precision:", precision_score(y_real, preds_cls))
        print("Recall:", recall_score(y_real, preds_cls))
        print("F1:", f1_score(y_real, preds_cls))
        
    print("Finished evaluating.")
    
if __name__ == '__main__':
    evaluate()
