import pandas as pd
import numpy as np
from pathlib import Path
import json

# Adjust imports to local src if running from repo root
import sys
sys.path.append('src')

from ertmac.ml.features import construct_causal_features, CausalFeatureConfig
from ertmac.ml.dataset import generate_deterministic_negatives
from ertmac.ml.inference import DataQualityGate

def parse_date(date_str):
    try:
        return pd.to_datetime(date_str, utc=True)
    except:
        return pd.NaT

def main():
    print("Loading data...")
    events = pd.read_csv('reports/tables/verified_event_episodes_v2.csv')
    usrop = pd.read_parquet('data/processed/usrop/usrop_clean.parquet')
    ddr = pd.read_parquet('volve_ddr.parquet')
    
    # 1. Map columns in USROP
    col_map = {
        'Measured Depth m': 'md',
        'Weight on Bit kkgf': 'wob',
        'Average Standpipe Pressure kPa': 'spp',
        'Average Surface Torque kN.m': 'torque',
        'Rate of Penetration m/h': 'rop',
        'Average Rotary Speed rpm': 'rpm',
        'Mud Flow In L/min': 'flow_in',
        'Mud Density In g/cm3': 'mud_density',
        'Diameter mm': 'diameter',
        'Average Hookload kkgf': 'hookload',
        'Hole Depth (TVD) m': 'tvd',
        'USROP Gamma gAPI': 'gamma',
        'well_id': 'well_id'
    }
    usrop = usrop.rename(columns=col_map)
    # The dataset functions might expect 'wellbore_id'
    usrop['wellbore_id'] = usrop['well_id'].apply(lambda x: "NO " + x)
    
    # 2. Filter events
    # We want HIGH confidence mud loss
    events = events[events['onset_confidence'] == 'HIGH'].copy()
    events = events[events['event_type'].str.contains('MUD_LOSS')].copy()
    
    # 3. Well mapping and Coverage
    usrop_wells = usrop['well_id'].unique().tolist()
    well_coverage = {}
    valid_events = []
    
    for u_well in usrop_wells:
        ddr_w = "NO " + u_well
        matched = events[events['wellbore_id'].str.startswith(ddr_w, na=False)].copy()
        well_coverage[u_well] = len(matched)
        
        # Override wellbore_id in matched events to exactly match our mapping for simplicity
        if not matched.empty:
            matched['wellbore_id'] = ddr_w
            valid_events.append(matched)
            
    df_pos = pd.concat(valid_events, ignore_index=True) if valid_events else pd.DataFrame()
    
    zero_coverage_wells = [w for w, c in well_coverage.items() if c == 0]
    print(f"Wells with zero coverage: {zero_coverage_wells}")
    
    if df_pos.empty:
        print("No positive events to process.")
        return
        
    df_pos['md'] = df_pos['onset_md'] # dataset.py needs 'md'
    
    # Generate Negatives
    print("Generating negatives...")
    df_neg = generate_deterministic_negatives(
        df_sensors=usrop,
        df_events=df_pos,
        target_event_type='FORMATION_MUD_LOSS',
        ratio=5,
        exclusion_zone_m=50.0
    )
    
    # 4. Feature Extraction & Quality Gates
    features_list = []
    quality_gate = DataQualityGate(required_history_md=25.0)
    config = CausalFeatureConfig(windows=[5.0, 10.0, 25.0, 50.0])
    
    report_gate_results = []
    
    def get_activity_phase(wb, ts_str):
        ts = parse_date(ts_str)
        if pd.isna(ts): return "Unknown"
        ddr_w = ddr[ddr['nameWellbore'] == wb]
        for _, dr in ddr_w.iterrows():
            start = parse_date(dr['dTimStart'])
            if pd.notna(start) and start.date() == ts.date():
                acts = dr['activity']
                if acts is not None and len(acts) > 0:
                    for act in acts:
                        a_start = parse_date(act.get('dTimStart'))
                        a_end = parse_date(act.get('dTimEnd'))
                        if pd.notna(a_start) and pd.notna(a_end) and a_start <= ts <= a_end:
                            return f"{act.get('phase', '')}/{act.get('proprietaryCode', '')}"
        return "Unknown/No Match"

    # Process Positives
    for idx, row in df_pos.iterrows():
        wb = row['wellbore_id']
        onset = row['onset_md']
        cutoff_md = onset - 25.0 # 25m causal lookback horizon
        ts_str = row['onset_timestamp']
        
        well_data = usrop[usrop['wellbore_id'] == wb].copy()
        history = well_data[well_data['md'] <= cutoff_md]
        
        status = quality_gate.check_quality(history, cutoff_md, wb)
        report_gate_results.append({'well_id': wb, 'type': 'positive', 'status': status, 'cutoff_md': cutoff_md})
        
        if status == 'PASS':
            try:
                feats = construct_causal_features(history, cutoff_md, config)
                feats['well_id'] = wb.replace("NO ", "")
                feats['is_event'] = 1
                feats['onset_md'] = onset
                feats['cutoff_md'] = cutoff_md
                feats['ddr_activity_phase'] = get_activity_phase(wb, ts_str)
                features_list.append(feats)
            except Exception as e:
                report_gate_results.append({'well_id': wb, 'type': 'positive', 'status': f"FAIL_EXTRACT: {e}", 'cutoff_md': cutoff_md})
                
    # Process Negatives
    if not df_neg.empty:
        for idx, row in df_neg.iterrows():
            wb = row['wellbore_id']
            onset = row['md']
            cutoff_md = onset - 25.0
            
            well_data = usrop[usrop['wellbore_id'] == wb].copy()
            history = well_data[well_data['md'] <= cutoff_md]
            
            status = quality_gate.check_quality(history, cutoff_md, wb)
            report_gate_results.append({'well_id': wb, 'type': 'negative', 'status': status, 'cutoff_md': cutoff_md})
            
            if status == 'PASS':
                try:
                    feats = construct_causal_features(history, cutoff_md, config)
                    feats['well_id'] = wb.replace("NO ", "")
                    feats['is_event'] = 0
                    feats['onset_md'] = onset
                    feats['cutoff_md'] = cutoff_md
                    feats['ddr_activity_phase'] = 'NEGATIVE_SAMPLE'
                    features_list.append(feats)
                except Exception as e:
                    pass
                    
    # Output Parquet
    df_features = pd.DataFrame(features_list)
    out_dir = Path('data/processed/real_training')
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if len(df_features) > 0:
        parquet_path = out_dir / 'mud_loss_real_v1.parquet'
        df_features.to_parquet(parquet_path, index=False)
        print(f"Saved dataset with shape {df_features.shape}")
    else:
        print("No valid features generated.")
    
    # 5. Reporting
    report_df = pd.DataFrame(report_gate_results)
    
    # Count passed positives with non-drilling phases
    non_drilling_positives = 0
    if not df_features.empty:
        pos_df = df_features[df_features['is_event'] == 1]
        for p in pos_df['ddr_activity_phase']:
            if 'drill' not in str(p).lower():
                non_drilling_positives += 1
    
    report_md = f"""# Real Data Merge Report (Mud Loss)
    
## Well ID Reconciliation
USROP Wells: {usrop_wells}
Wells with 0 valid events (Event-Negative-Only): {zero_coverage_wells}

## Event Counts (HIGH Confidence)
Total Mud Loss POSITIVES: {len(df_pos)}
Total Valid POSITIVES passing Data Gate: {len(df_features[df_features['is_event'] == 1]) if not df_features.empty else 0}
(Of which, {non_drilling_positives} occurred during non-drilling activities like tripping/circulating)

Total sampled NEGATIVES: {len(df_neg)}
Total Valid NEGATIVES passing Data Gate: {len(df_features[df_features['is_event'] == 0]) if not df_features.empty else 0}

## Class Balance (Final Dataset)
Total Rows: {len(df_features) if not df_features.empty else 0}
Positive: {len(df_features[df_features['is_event'] == 1]) if not df_features.empty else 0}
Negative: {len(df_features[df_features['is_event'] == 0]) if not df_features.empty else 0}

## Data Quality Gate Details
"""
    
    status_counts = report_df['status'].value_counts()
    for s, c in status_counts.items():
        report_md += f"- {s}: {c}\n"
        
    with open('reports/real_data_merge_report.md', 'w') as f:
        f.write(report_md)
        
if __name__ == "__main__":
    main()
