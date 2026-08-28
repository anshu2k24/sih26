import pandas as pd
import numpy as np
import sys
from pathlib import Path
from scipy import stats

sys.path.append('src')

from ertmac.ml.features import construct_causal_features, CausalFeatureConfig
from ertmac.ml.dataset import generate_deterministic_negatives
from ertmac.ml.models import LightGBMBaseline
from ertmac.ml.inference import DataQualityGate

def main():
    print("Loading synthetic data for model training...")
    try:
        df_events_syn = pd.read_parquet('data/synthetic/oil_ertmac_events.parquet')
        df_sensors_syn = pd.read_parquet('data/synthetic/oil_ertmac_sensors.parquet')
    except Exception as e:
        print(f"Error loading synthetic data: {e}")
        return

    # 1. Build Synthetic Training Features
    target_event = 'FORMATION_MUD_LOSS'
    print(f"Building synthetic features for {target_event}...")
    
    pos_events = df_events_syn[df_events_syn['event_type'] == target_event].copy()
    df_negatives = generate_deterministic_negatives(
        df_sensors_syn, df_events_syn, target_event_type=target_event, 
        ratio=3, random_seed=42, exclusion_zone_m=50.0
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
            feature_rows.append(feats)
        except:
            pass

    df_train = pd.DataFrame(feature_rows)
    if df_train.empty:
        print("Failed to build synthetic training set.")
        return
        
    print(f"Training LightGBM on {len(df_train)} synthetic samples...")
    X_train = df_train.drop(columns=['is_event'])
    
    # Ensure numeric types
    X_train = X_train.select_dtypes(include=[np.number])
    y_train = df_train['is_event']
    
    model = LightGBMBaseline()
    model.fit(X_train, y_train)
    
    # Get score distribution on synthetic negatives
    X_train_neg = X_train[y_train == 0]
    syn_neg_scores = model.predict_proba(X_train_neg)
    
    # 2. Extract Real Features
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

    target_etypes = ['FORMATION_MUD_LOSS', 'Equipment Failure', 'Pack-off']
    gate = DataQualityGate(required_history_md=25.0)

    results = []
    
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
            
            status = gate.check_quality(hist, cutoff, wb)
            if status == 'PASS':
                try:
                    feats = construct_causal_features(hist, cutoff, config)
                    
                    # Convert to dataframe and match columns
                    feat_df = pd.DataFrame([feats])
                    # Add missing columns with 0
                    for c in X_train.columns:
                        if c not in feat_df.columns:
                            feat_df[c] = 0.0
                    feat_df = feat_df[X_train.columns] # Reorder to match training
                    
                    score = model.predict_proba(feat_df)[0]
                    percentile = stats.percentileofscore(syn_neg_scores, score)
                    
                    results.append({
                        'event_type': etype,
                        'wellbore_id': wb,
                        'onset_md': onset,
                        'raw_score': score,
                        'percentile': percentile
                    })
                except Exception as e:
                    pass

    # 3. Report Results
    report = []
    report.append("# Out-of-Distribution Validation on Real Events")
    report.append("This is an informal sanity check (read-only) evaluating the production synthetic-trained model against the 7 real passing events. It compares the model's raw risk score to its baseline distribution on clean synthetic data to produce a percentile rank.")
    report.append("\n**Important Caveat**: n=7 is statistically insignificant. These results represent qualitative informal evidence, not a claim of definitive mathematical generalization.")
    
    report.append("\n## Results Table")
    report.append("| Event Type | Wellbore | Onset MD | Predicted Risk Score | Percentile (vs Normal) | Gate Status |")
    report.append("|---|---|---|---|---|---|")
    
    elevated_threshold = 85.0 # Consider > 85th percentile "elevated risk"
    elevated_count = 0
    
    for res in results:
        is_elevated = res['percentile'] > elevated_threshold
        if is_elevated: elevated_count += 1
        
        report.append(f"| {res['event_type']} | {res['wellbore_id']} | {res['onset_md']} | {res['raw_score']:.3f} | {res['percentile']:.1f}% | PASS |")
        
    report.append(f"\n## Summary")
    report.append(f"**{elevated_count} of {len(results)}** real events scored in the elevated-risk range (>85th percentile).")
    report.append(f"**{len(results) - elevated_count} of {len(results)}** real events did not show elevated risk.")
    
    with open('reports/ood_real_event_validation.md', 'w') as f:
        f.write("\n".join(report))
        
    print("OOD validation complete.")

if __name__ == "__main__":
    main()
