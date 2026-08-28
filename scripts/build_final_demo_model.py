import pandas as pd
import numpy as np
import sys
import os
import random
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import roc_auc_score, average_precision_score
import joblib

sys.path.append('src')
from ertmac.ml.features import construct_causal_features, CausalFeatureConfig
from ertmac.ml.models import LogisticRegressionBaseline
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

def perturb_series(df_hist, etype, cutoff):
    """
    Apply realistic perturbations mimicking real events.
    Returns a modified copy of df_hist.
    """
    df = df_hist.copy()
    
    # Identify the perturbation window (last 25m)
    mask = (df['md'] >= cutoff - 25.0) & (df['md'] <= cutoff)
    
    if etype == 'FORMATION_MUD_LOSS':
        # SPP drop -15% to -34%, Flow In drop
        drop_factor = random.uniform(0.66, 0.85)
        if 'spp' in df.columns:
            noise = np.random.normal(0, 0.05 * df.loc[mask, 'spp'].mean(), size=mask.sum())
            df.loc[mask, 'spp'] = df.loc[mask, 'spp'] * drop_factor + noise
        if 'flow_in' in df.columns:
            df.loc[mask, 'flow_in'] = df.loc[mask, 'flow_in'] * drop_factor
            
    elif etype == 'Pack-off':
        # SPP surge +20-35% + torque volatility
        surge_factor = random.uniform(1.20, 1.35)
        if 'spp' in df.columns:
            df.loc[mask, 'spp'] = df.loc[mask, 'spp'] * surge_factor
        if 'torque' in df.columns:
            volatility = np.random.normal(0, 0.20 * df.loc[mask, 'torque'].mean(), size=mask.sum())
            df.loc[mask, 'torque'] = df.loc[mask, 'torque'] + volatility
            
    elif etype == 'Equipment Failure':
        # ROP slowdown pattern
        if 'rop' in df.columns:
            slowdown = np.linspace(1.0, random.uniform(0.2, 0.5), mask.sum())
            noise = np.random.normal(0, 0.1 * df.loc[mask, 'rop'].mean(), size=mask.sum())
            df.loc[mask, 'rop'] = df.loc[mask, 'rop'] * slowdown + noise
            
    return df

def clean_features(feat_dict):
    """Remove ratio features to avoid Infinity bug."""
    clean = {}
    for k, v in feat_dict.items():
        if any(x in k for x in ['ratio', 'rel_delta', 'cv', 'norm_slope']):
            continue
        # Check for inf/nan
        if np.isinf(v) or pd.isna(v):
            clean[k] = np.nan
        else:
            clean[k] = v
    return clean

def main():
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
    
    config = CausalFeatureConfig(windows=[5.0, 10.0, 25.0, 50.0])
    gate = DataQualityGate(required_history_md=25.0)
    
    dataset_rows = []
    target_etypes = ['FORMATION_MUD_LOSS', 'Equipment Failure', 'Pack-off']
    all_wells = usrop['wellbore_id'].unique()
    
    # 1. Real Positives
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
                    dataset_rows.append(feats)
                except:
                    pass
                    
    # 3. Identify Gap and Inject Synthetic
    zero_pos_wells = [w for w in all_wells if w not in real_pos_wells]
    print(f"Zero Real Positive Wells: {zero_pos_wells}")
    
    # Inject synthetics to balance
    for wb in zero_pos_wells:
        # Get up to 10 safe anchors for injection per event type
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
                        # Perturb
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

    df = pd.DataFrame(dataset_rows)
    df = df.replace([np.inf, -np.inf], np.nan)
    
    print(df['source'].value_counts())
    real_pct = (df['source'].isin(['real_event', 'real_negative'])).mean() * 100
    syn_pct = (df['source'] == 'synthetic_anchored_positive').mean() * 100
    
    # Train and Evaluate
    X = df.drop(columns=['is_event', 'group', 'source', 'event_type']).select_dtypes(include=[np.number])
    y = df['is_event']
    groups = df['group']
    
    logo = LeaveOneGroupOut()
    fold_metrics = []
    
    for train_idx, test_idx in logo.split(X, y, groups):
        # We need both classes in train
        if y.iloc[train_idx].nunique() < 2: continue
        
        test_group = groups.iloc[test_idx].iloc[0]
        # Check if the test positive class contains synthetic
        test_pos_sources = df.iloc[test_idx][df.iloc[test_idx]['is_event'] == 1]['source'].unique()
        has_syn_pos = 'synthetic_anchored_positive' in test_pos_sources
        
        model = LogisticRegressionBaseline()
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        preds = model.predict_proba(X.iloc[test_idx])
        
        if len(np.unique(y.iloc[test_idx])) > 1:
            auc = roc_auc_score(y.iloc[test_idx], preds)
            pr = average_precision_score(y.iloc[test_idx], preds)
            fold_metrics.append({
                'fold': test_group,
                'has_synthetic_pos': has_syn_pos,
                'auc': auc,
                'pr_auc': pr
            })
            
    # Final model on all data
    final_model = LogisticRegressionBaseline()
    final_model.fit(X, y)
    
    # Save model
    os.makedirs('models', exist_ok=True)
    model_path = 'models/ertmac_production_v1.joblib'
    joblib.dump(final_model, model_path)
    
    # Model Card
    card = []
    card.append("# Model Card: eRTMAC-NWIS Production Risk Classifier v1")
    card.append("\n## Provenance")
    card.append("- **Model Architecture**: Logistic Regression (Linear Baseline)")
    card.append("- **Feature Strategy**: Causal Window Statistics with Well-Relative Normalization (Z-Score on causal history)")
    card.append("- **Training Dataset Strategy**: Real Primary + Synthetic-Anchored Fill")
    
    card.append("\n## Dataset Composition")
    card.append(f"- **Total Training Rows**: {len(df)}")
    card.append(f"- **Real Data Proportion**: {real_pct:.1f}%")
    card.append(f"- **Synthetic-Anchored Proportion**: {syn_pct:.1f}%")
    card.append("\n**Row Breakdowns by Source:**")
    counts = df['source'].value_counts()
    for k, v in counts.items(): card.append(f"- {k}: {v}")
    
    card.append("\n## The Gap & Synthetic Fill")
    card.append("Due to structural sparsity in the Volve DDR record, several wells had zero real positive events in the historical data, blocking cross-validation.")
    card.append(f"**Zero-Positive Wells Filled:** {', '.join(zero_pos_wells)}")
    card.append("\nFor these wells, we sampled real normal causal windows (using real telemetry and baselines) and explicitly perturbed the final 25m according to observed real signatures:")
    card.append("- **FORMATION_MUD_LOSS**: SPP dropped -15% to -34%, Flow In dropped")
    card.append("- **Pack-off**: SPP surged +20% to +35% with elevated torque volatility")
    card.append("- **Equipment Failure**: ROP steady decay / slowdown")
    
    card.append("\n## Performance Metrics (Leave-One-Well-Out Cross Validation)")
    card.append("Validation folds were strictly separated by `wellbore_id` to ensure no spatial leakage.")
    
    df_metrics = pd.DataFrame(fold_metrics)
    if not df_metrics.empty:
        real_folds = df_metrics[~df_metrics['has_synthetic_pos']]
        syn_folds = df_metrics[df_metrics['has_synthetic_pos']]
        
        card.append(f"\n**Pooled Average (All Folds)**")
        card.append(f"- ROC-AUC: {df_metrics['auc'].mean():.3f}")
        card.append(f"- PR-AUC: {df_metrics['pr_auc'].mean():.3f}")
        
        card.append(f"\n**Performance on 100% REAL Positive Folds** (Folds where the tested events were actual Volve failures)")
        if not real_folds.empty:
            card.append(f"- ROC-AUC: {real_folds['auc'].mean():.3f}")
            card.append(f"- PR-AUC: {real_folds['pr_auc'].mean():.3f}")
        else:
            card.append("- No metric available (no folds were purely real)")
            
        card.append(f"\n**Performance on SYNTHETIC-ANCHORED Positive Folds**")
        if not syn_folds.empty:
            card.append(f"- ROC-AUC: {syn_folds['auc'].mean():.3f}")
            card.append(f"- PR-AUC: {syn_folds['pr_auc'].mean():.3f}")
            
    with open('reports/model_card_v1.md', 'w') as f:
        f.write("\n".join(card))
        
    print("Demo dataset generated, model trained, and card saved.")

if __name__ == "__main__":
    main()
