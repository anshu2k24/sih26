import pandas as pd
import numpy as np
import random
import os
import glob
from pathlib import Path

def run_audit():
    # 2. CONTAMINATED ARTIFACTS
    contaminated = []
    contaminated.append({
        'artifact': 'models/ertmac_production_v1.joblib',
        'type': 'model',
        'contains_synthetic': True,
        'synthetic_count': 45,
        'real_count': 943,
        'safe_for_real_ml': False,
        'reason': 'Trained on leaked synthetic-anchored positives generated from real negative windows'
    })
    contaminated.append({
        'artifact': 'reports/model_card_v1.md',
        'type': 'metric report',
        'contains_synthetic': True,
        'synthetic_count': 45,
        'real_count': 943,
        'safe_for_real_ml': False,
        'reason': 'Reports cross-validation metrics computed on synthetic-contaminated folds'
    })
    # Search for other artifacts referencing synthetic-anchored
    for f in glob.glob('reports/tables/*.csv'):
        try:
            df = pd.read_csv(f)
            if 'source' in df.columns:
                if 'synthetic_anchored_positive' in df['source'].values:
                    contaminated.append({
                        'artifact': f,
                        'type': 'experiment output',
                        'contains_synthetic': True,
                        'synthetic_count': (df['source'] == 'synthetic_anchored_positive').sum(),
                        'real_count': len(df) - (df['source'] == 'synthetic_anchored_positive').sum(),
                        'safe_for_real_ml': False,
                        'reason': 'Contains synthetic-anchored positives'
                    })
        except:
            pass
            
    df_contam = pd.DataFrame(contaminated)
    os.makedirs('reports/tables', exist_ok=True)
    df_contam.to_csv('reports/tables/contaminated_artifacts.csv', index=False)

    # 3. REAL ONLY SOURCE INVENTORY
    sources = [
        {
            'file': 'data/processed/usrop/usrop_clean.parquet',
            'type': 'real Volve sensor data',
            'safe_for_real_ml': True
        },
        {
            'file': 'reports/tables/verified_event_episodes_v2.csv',
            'type': 'verified real event episodes',
            'safe_for_real_ml': True
        }
    ]
    pd.DataFrame(sources).to_csv('reports/tables/real_only_source_inventory.csv', index=False)
    
    # 4 & 5. REAL POSITIVE & NEGATIVE INVENTORY
    events = pd.read_csv('reports/tables/verified_event_episodes_v2.csv')
    usrop = pd.read_parquet('data/processed/usrop/usrop_clean.parquet')
    
    events = events[events['event_type'] == 'FORMATION_MUD_LOSS']
    events = events[events['onset_confidence'] == 'HIGH']
    
    col_map = {'well_id': 'well_id', 'Measured Depth m': 'md'}
    usrop = usrop.rename(columns=col_map)
    usrop['wellbore_id'] = usrop['well_id'].apply(lambda x: "NO " + x)
    
    usrop_wells = usrop['wellbore_id'].unique()
    overlap_rows = []
    
    for idx, r in events.iterrows():
        wb = r['wellbore_id']
        onset = r['onset_md']
        if wb not in usrop_wells:
            continue
            
        w_df = usrop[usrop['wellbore_id'] == wb]
        min_md = w_df['md'].min()
        max_md = w_df['md'].max()
        
        if pd.isna(min_md) or pd.isna(max_md) or pd.isna(onset):
            continue
            
        valid_25 = min_md <= (onset - 25.0) and max_md >= onset
        valid_50 = min_md <= (onset - 50.0) and max_md >= onset
        valid_100 = min_md <= (onset - 100.0) and max_md >= onset
        
        if valid_25:
            overlap_rows.append({
                'event_episode_id': idx,
                'DDR_well': wb,
                'sensor_well': wb.replace("NO ", ""),
                'independent_group': wb,
                'onset_md': onset,
                '25m_valid': valid_25,
                '50m_valid': valid_50,
                '100m_valid': valid_100,
                'primary_source': 'real_event'
            })
            
    df_overlap = pd.DataFrame(overlap_rows)
    df_overlap.to_csv('reports/tables/real_fml_sensor_overlap.csv', index=False)
    
    # Negatives
    total_safe_negatives = 0
    neg_wells = 0
    for wb in usrop_wells:
        w_df = usrop[usrop['wellbore_id'] == wb]
        if w_df.empty: continue
        min_md = w_df['md'].min() + 50.0
        max_md = w_df['md'].max()
        
        if np.isnan(min_md) or np.isnan(max_md): continue
        
        wb_events = events[events['wellbore_id'] == wb]
        exclusions = []
        for _, r in wb_events.iterrows():
            onset = r['onset_md']
            if pd.notna(onset):
                exclusions.append((onset - 100.0, onset + 100.0))
                
        # Estimate total possible safe windows (e.g., every 25m step)
        safe_count = 0
        md = min_md
        while md <= max_md:
            is_safe = True
            for e_min, e_max in exclusions:
                if e_min <= md <= e_max:
                    is_safe = False
                    break
            if is_safe:
                safe_count += 1
            md += 25.0
            
        if safe_count > 0:
            total_safe_negatives += safe_count
            neg_wells += 1
            
    print(f"REAL FML EPISODES: {len(overlap_rows)}")
    print(f"REAL INDEPENDENT GROUPS (WELLS): {df_overlap['independent_group'].nunique() if len(overlap_rows) > 0 else 0}")
    print(f"SAFE REAL NEGATIVES: {total_safe_negatives}")

if __name__ == '__main__':
    run_audit()
