#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("build_sensor_dataset")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
USROP_PATH = DATA_DIR / "processed" / "usrop" / "usrop_clean.parquet"
EVENTS_DIR = DATA_DIR / "processed" / "events"
SENSORS_DIR = DATA_DIR / "processed" / "sensors"
SENSORS_DIR.mkdir(parents=True, exist_ok=True)

TABLES_DIR = REPO_ROOT / "reports" / "tables"
REPORTS_DIR = REPO_ROOT / "reports"

VERIFIED_PATH = TABLES_DIR / "verified_event_episodes_v2.csv"

def main():
    logger.info("Starting Sensor Integration Pipeline")
    
    # -------------------------------------------------------------------
    # PHASE 1: Source Discovery
    # -------------------------------------------------------------------
    df_usrop = pd.read_parquet(USROP_PATH)
    
    inv_file = [{
        "source_name": "usrop_clean.parquet",
        "file_path": str(USROP_PATH),
        "file_size_mb": USROP_PATH.stat().st_size / (1024*1024),
        "total_rows": len(df_usrop),
        "unique_wells": df_usrop['well_id'].nunique(),
        "has_depth": 'Measured Depth m' in df_usrop.columns,
        "has_time": False, # USROP typically depth-indexed only unless there's a timestamp
        "status": "CONFIRMED FROM FILE"
    }]
    pd.DataFrame(inv_file).to_csv(TABLES_DIR / "witsml_sensor_file_inventory.csv", index=False)
    
    inv_chan = []
    for col in df_usrop.columns:
        inv_chan.append({
            "source_name": "usrop_clean.parquet",
            "channel_name": col,
            "non_null_count": df_usrop[col].notnull().sum(),
            "inferred_unit": col.split(' ')[-1] if ' ' in col else "unknown",
            "status": "CONFIRMED FROM FILE"
        })
    pd.DataFrame(inv_chan).to_csv(TABLES_DIR / "witsml_channel_inventory.csv", index=False)
    
    # -------------------------------------------------------------------
    # PHASE 2: Well Identifier Reconciliation
    # -------------------------------------------------------------------
    df_ver = pd.read_csv(VERIFIED_PATH)
    ddr_wells = df_ver['wellbore_id'].unique()
    usrop_wells = df_usrop['well_id'].unique()
    
    mapping = []
    for dw in ddr_wells:
        norm_dw = dw.replace('NO ', '')
        if norm_dw in usrop_wells:
            mapping.append({
                "source": "DDR->USROP",
                "raw_identifier": dw,
                "normalized_identifier": dw,
                "canonical_well_id": dw,
                "canonical_wellbore_id": dw,
                "mapping_confidence": "HIGH",
                "mapping_reason": "Exact string match between DDR wellbore and USROP well_id"
            })
        else:
            mapping.append({
                "source": "DDR->USROP",
                "raw_identifier": dw,
                "normalized_identifier": dw,
                "canonical_well_id": np.nan,
                "canonical_wellbore_id": np.nan,
                "mapping_confidence": "AMBIGUOUS",
                "mapping_reason": "No match found in USROP dataset"
            })
    pd.DataFrame(mapping).to_csv(TABLES_DIR / "well_identifier_mapping.csv", index=False)
    
    # -------------------------------------------------------------------
    # PHASE 5: Causal Event Join & PHASE 6: Negative Sampling
    # -------------------------------------------------------------------
    # We only care about FORMATION_MUD_LOSS
    df_fml = df_ver[df_ver['event_type'] == 'FORMATION_MUD_LOSS'].copy()
    
    horizons = [25, 50, 100]
    
    join_audit = []
    examples = []
    
    # Pre-sort USROP for fast lookup
    df_usrop = df_usrop.sort_values(['well_id', 'Measured Depth m']).reset_index(drop=True)
    
    episode_id_counter = 0
    
    # Process Positives
    for _, ep in df_fml.iterrows():
        wb = ep['wellbore_id']
        o_md = ep['onset_md']
        if pd.isnull(o_md): continue
        norm_wb = wb.replace('NO ', '')
        if norm_wb not in usrop_wells:
            join_audit.append({
                "event_episode_id": ep['event_episode_id'],
                "wellbore_id": wb,
                "onset_md": o_md,
                "horizon_m": np.nan,
                "join_status": "UNRESOLVED",
                "reason": "Wellbore not in sensor data"
            })
            continue
            
        wb_data = df_usrop[df_usrop['well_id'] == norm_wb]
        
        for h in horizons:
            cutoff_md = o_md - h
            
            # Find sensor data BEFORE cutoff
            past_data = wb_data[wb_data['Measured Depth m'] <= cutoff_md]
            if len(past_data) == 0:
                join_audit.append({
                    "event_episode_id": ep['event_episode_id'],
                    "wellbore_id": wb,
                    "onset_md": o_md,
                    "horizon_m": h,
                    "join_status": "UNRESOLVED",
                    "reason": "No sensor history before cutoff"
                })
                continue
                
            # Latest sensor observation
            latest = past_data.iloc[-1]
            dist = cutoff_md - latest['Measured Depth m']
            
            join_status = "DEPTH_NEAREST" if dist > 0.5 else "EXACT"
            
            join_audit.append({
                "event_episode_id": ep['event_episode_id'],
                "wellbore_id": wb,
                "onset_md": o_md,
                "horizon_m": h,
                "join_status": join_status,
                "reason": f"Joined at dist {dist:.2f}m"
            })
            
            # Add to examples (we'll just store the single row at cutoff for now, representing the "state")
            # In a real model, this would be a window/sequence.
            row_dict = latest.to_dict()
            row_dict['example_id'] = f"POS_{ep['event_episode_id']}_H{h}"
            row_dict['event_episode_id'] = ep['event_episode_id']
            row_dict['label'] = 1
            row_dict['horizon_m'] = h
            row_dict['onset_md'] = o_md
            row_dict['prediction_cutoff_md'] = cutoff_md
            row_dict['lead_distance_m'] = o_md - latest['Measured Depth m']
            
            examples.append(row_dict)
            
    # Process Negatives
    # Negative policy: outside [-50m, +50m] buffer of ANY verified event for that well.
    # We will sample 5 negatives per well per horizon, evenly spaced.
    buffer = 50
    for wb in df_ver['wellbore_id'].unique():
        norm_wb = wb.replace('NO ', '')
        if norm_wb not in usrop_wells: continue
        
        wb_data = df_usrop[df_usrop['well_id'] == norm_wb]
        wb_events = df_ver[df_ver['wellbore_id'] == wb]
        
        valid_mask = np.ones(len(wb_data), dtype=bool)
        for _, ep in wb_events.iterrows():
            o_md = ep['onset_md']
            if pd.isnull(o_md): continue
            m = (wb_data['Measured Depth m'] >= o_md - buffer) & (wb_data['Measured Depth m'] <= o_md + buffer)
            valid_mask[m] = False
            
        safe_data = wb_data[valid_mask]
        
        if len(safe_data) > 0:
            # Pick ~10 safe rows spaced out
            idx_sampled = np.linspace(0, len(safe_data)-1, min(10, len(safe_data)), dtype=int)
            safe_samples = safe_data.iloc[idx_sampled]
            
            for h in horizons:
                for i, (_, row) in enumerate(safe_samples.iterrows()):
                    row_dict = row.to_dict()
                    row_dict['example_id'] = f"NEG_{norm_wb}_{i}_H{h}"
                    row_dict['event_episode_id'] = "NONE"
                    row_dict['label'] = 0
                    row_dict['horizon_m'] = h
                    row_dict['onset_md'] = np.nan
                    row_dict['prediction_cutoff_md'] = row['Measured Depth m']
                    row_dict['lead_distance_m'] = np.nan
                    
                    examples.append(row_dict)

    df_join_audit = pd.DataFrame(join_audit)
    df_join_audit.to_csv(TABLES_DIR / "event_sensor_join_audit.csv", index=False)
    
    df_examples = pd.DataFrame(examples)
    df_examples.to_parquet(EVENTS_DIR / "event_sensor_examples.parquet", index=False)
    
    # -------------------------------------------------------------------
    # PHASE 7: LEAKAGE AUDIT
    # ---------------------------------------------------------
    leak_audit = []
    for _, ex in df_examples.iterrows():
        latest_md = ex['Measured Depth m']
        cutoff_md = ex['prediction_cutoff_md']
        o_md = ex['onset_md']
        
        feature_max_md = latest_md # since we only extracted the single row <= cutoff
        
        # Leakage violations
        violates_cutoff = feature_max_md > cutoff_md
        violates_onset = pd.notnull(o_md) and feature_max_md >= o_md
        
        leak_flag = violates_cutoff or violates_onset
        
        leak_audit.append({
            "example_id": ex['example_id'],
            "label": ex['label'],
            "prediction_cutoff_md": cutoff_md,
            "event_onset_md": o_md,
            "lead_distance_m": ex['lead_distance_m'],
            "latest_feature_md": latest_md,
            "latest_feature_timestamp": np.nan, # USROP has no time
            "feature_max_md": feature_max_md,
            "event_text_present": False,
            "mitigation_text_present": False,
            "post_onset_sensor_present": violates_onset,
            "leakage_flag": leak_flag
        })
        
    df_leak = pd.DataFrame(leak_audit)
    df_leak.to_csv(TABLES_DIR / "event_sensor_leakage_audit.csv", index=False)
    
    logger.info("Sensor Dataset Built.")

if __name__ == "__main__":
    main()
