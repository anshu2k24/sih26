import pandas as pd
import numpy as np
import sys
import os
import joblib

sys.path.append('src')
from ertmac.ml.features import construct_causal_features, CausalFeatureConfig
from ertmac.ml.inference import DataQualityGate
from ertmac.ml.inference import load_production_model

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
    print("Loading data...")
    usrop = pd.read_parquet('data/processed/usrop/usrop_clean.parquet')
    events = pd.read_csv('reports/tables/verified_event_episodes_v2.csv')
    
    col_map = {
        'Measured Depth m': 'md', 'Weight on Bit kkgf': 'wob', 'Average Standpipe Pressure kPa': 'spp',
        'Average Surface Torque kN.m': 'torque', 'Rate of Penetration m/h': 'rop', 'Average Rotary Speed rpm': 'rpm',
        'Mud Flow In L/min': 'flow_in', 'Mud Density In g/cm3': 'mud_density', 'Diameter mm': 'diameter',
        'Average Hookload kkgf': 'hookload', 'Hole Depth (TVD) m': 'tvd', 'USROP Gamma gAPI': 'gamma'
    }
    usrop = usrop.rename(columns=col_map)
    usrop['wellbore_id'] = usrop['well_id'].apply(lambda x: 'NO ' + x)
    
    # Get the best event from our overlap CSV
    overlaps = pd.read_csv('reports/tables/real_fml_sensor_overlap.csv')
    if overlaps.empty:
        print("No valid events found in overlap CSV.")
        return
        
    target_event_row = overlaps.iloc[0]
    target_wb = target_event_row['DDR_well']
    onset = target_event_row['onset_md']
    
    w_df = usrop[usrop['wellbore_id'] == target_wb].sort_values('md')
    w_df = w_df[(w_df['md'] >= onset - 200.0) & (w_df['md'] <= onset + 10.0)]
    
    config = CausalFeatureConfig(windows=[5.0, 10.0, 25.0, 50.0])
    gate = DataQualityGate(required_history_md=25.0)
    
    try:
        model = load_production_model('models/volve_research_v1.joblib')
    except Exception as e:
        print(f"Model load error: {e}")
        return
        
    # We need to make sure X columns match model feature names
    # So we need one dummy extraction to get column names
    if hasattr(model, 'feature_names_in_'):
        feat_names = model.feature_names_in_
    else:
        # Fallback to getting it from a dummy extraction
        feat_names = None
    
    trace_rows = []
    
    # Replay
    buffer = []
    for idx, row in w_df.iterrows():
        current_md = row['md']
        # simulate buffer
        buffer_df = w_df[w_df['md'] <= current_md].copy()
        
        status = gate.check_quality(buffer_df, current_md, target_wb)
        
        risk_score = np.nan
        pred_avail = False
        
        if status == 'PASS':
            feats = construct_causal_features(buffer_df, current_md, config)
            feats = clean_features(feats)
            
            feat_df = pd.DataFrame([feats]).replace([np.inf, -np.inf], np.nan).fillna(0)
            
            if feat_names is not None:
                # ensure all columns are present
                for col in feat_names:
                    if col not in feat_df.columns:
                        feat_df[col] = 0.0
                X = feat_df[feat_names]
            else:
                X = feat_df
                
            try:
                preds = model.predict_proba(X)
                if preds.ndim == 2:
                    risk_score = preds[0, 1]
                else:
                    risk_score = preds[0]
                pred_avail = True
            except Exception as e:
                pass
                
        trace_rows.append({
            'timestamp': row.get('dTim', pd.Timestamp.now().isoformat()),
            'md': current_md,
            'risk_score': risk_score,
            'event_onset_md': onset,
            'distance_to_event': onset - current_md,
            'actual_label': 1 if (current_md >= onset) else 0,
            'prediction_available': pred_avail
        })
        
    df_trace = pd.DataFrame(trace_rows)
    os.makedirs('reports/ml', exist_ok=True)
    df_trace.to_csv('reports/ml/volve_replay_prediction_trace.csv', index=False)
    print(f"Generated trace with {len(df_trace)} rows")

if __name__ == '__main__':
    main()
