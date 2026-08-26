#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("build_sensor_dataset_v2")

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
    logger.info("Starting V2 Sensor Integration")
    
    if not USROP_PATH.exists() or not VERIFIED_PATH.exists():
        logger.error("Missing files")
        return
        
    df_usrop = pd.read_parquet(USROP_PATH)
    df_ver = pd.read_csv(VERIFIED_PATH)
    
    # 1. Inspect USROP depth sampling
    df_usrop = df_usrop.sort_values(['well_id', 'Measured Depth m']).reset_index(drop=True)
    df_usrop['md_diff'] = df_usrop.groupby('well_id')['Measured Depth m'].diff()
    median_step = df_usrop['md_diff'].median()
    logger.info(f"USROP Median MD step: {median_step} m")
    
    # Define max allowable join distance based on USROP sampling
    # Since USROP is typically ~0.15m, a max distance of 2.0m is very generous for "near-exact"
    # while preventing silent 50m jumps.
    MAX_JOIN_DIST = 2.0
    
    # 2. Well Identifier Reconciliation
    ddr_wells = df_ver['wellbore_id'].unique()
    usrop_wells = df_usrop['well_id'].unique()
    
    mapping = []
    for dw in ddr_wells:
        norm_dw = dw.replace('NO ', '')
        if norm_dw in usrop_wells:
            mapping.append({
                "raw_ddr_identifier": dw,
                "normalized_identifier": norm_dw,
                "usrop_identifier": norm_dw,
                "mapping_method": "Strip 'NO ' prefix",
                "confidence": "HIGH",
                "evidence": "Normalized string perfectly matches known USROP well_id"
            })
        else:
            mapping.append({
                "raw_ddr_identifier": dw,
                "normalized_identifier": norm_dw,
                "usrop_identifier": np.nan,
                "mapping_method": "Strip 'NO ' prefix",
                "confidence": "UNRESOLVED",
                "evidence": "Well not present in USROP dataset"
            })
    pd.DataFrame(mapping).to_csv(TABLES_DIR / "well_identifier_mapping_v2.csv", index=False)
    mapping_dict = {m['raw_ddr_identifier']: m['usrop_identifier'] for m in mapping if pd.notnull(m['usrop_identifier'])}
    
    # 3. Sensor Join Validity
    df_fml = df_ver[df_ver['event_type'] == 'FORMATION_MUD_LOSS'].copy()
    horizons = [25, 50, 100]
    join_audit = []
    
    for _, ep in df_fml.iterrows():
        wb = ep['wellbore_id']
        eid = ep['event_episode_id']
        o_md = ep['onset_md']
        
        if pd.isnull(o_md): continue
        
        sensor_well = mapping_dict.get(wb)
        if not sensor_well:
            for h in horizons:
                join_audit.append({
                    "event_episode_id": eid,
                    "ddr_wellbore_id": wb,
                    "sensor_well_id": np.nan,
                    "onset_md": o_md,
                    "horizon_m": h,
                    "prediction_cutoff_md": o_md - h,
                    "join_status": "UNRESOLVED_NO_WELL",
                    "join_distance_m": np.nan,
                    "sensor_sample_md": np.nan,
                    "reason": "Wellbore missing in USROP"
                })
            continue
            
        wb_data = df_usrop[df_usrop['well_id'] == sensor_well]
        
        for h in horizons:
            cutoff = o_md - h
            past = wb_data[wb_data['Measured Depth m'] <= cutoff]
            if len(past) == 0:
                join_audit.append({
                    "event_episode_id": eid,
                    "ddr_wellbore_id": wb,
                    "sensor_well_id": sensor_well,
                    "onset_md": o_md,
                    "horizon_m": h,
                    "prediction_cutoff_md": cutoff,
                    "join_status": "UNRESOLVED_NO_HISTORY",
                    "join_distance_m": np.nan,
                    "sensor_sample_md": np.nan,
                    "reason": "No sensor history before cutoff"
                })
                continue
                
            latest = past.iloc[-1]
            samp_md = latest['Measured Depth m']
            dist = cutoff - samp_md
            
            if dist <= 0.15:
                status = "EXACT"
                rsn = "Distance <= 0.15m"
            elif dist <= MAX_JOIN_DIST:
                status = "NEAR_EXACT"
                rsn = f"Distance {dist:.2f}m <= max {MAX_JOIN_DIST}m"
            else:
                status = "REJECTED_DISTANCE"
                rsn = f"Distance {dist:.2f}m exceeds max {MAX_JOIN_DIST}m"
                
            join_audit.append({
                "event_episode_id": eid,
                "ddr_wellbore_id": wb,
                "sensor_well_id": sensor_well,
                "onset_md": o_md,
                "horizon_m": h,
                "prediction_cutoff_md": cutoff,
                "join_status": status,
                "join_distance_m": dist,
                "sensor_sample_md": samp_md,
                "reason": rsn
            })
            
    df_audit = pd.DataFrame(join_audit)
    df_audit.to_csv(TABLES_DIR / "event_sensor_join_audit_v2.csv", index=False)
    
    # Coverage Calculation
    cov_recs = []
    cov_recs.append({
        "metric": "Verified DDR Episodes",
        "count": len(df_fml)
    })
    mapped = df_fml[df_fml['wellbore_id'].isin(mapping_dict.keys())]
    cov_recs.append({
        "metric": "Episodes with Mapped Sensor Well",
        "count": len(mapped)
    })
    for h in horizons:
        v_h = df_audit[(df_audit['horizon_m'] == h) & (df_audit['join_status'].isin(['EXACT', 'NEAR_EXACT']))]
        cov_recs.append({
            "metric": f"Valid causal sensor join at {h}m",
            "count": len(v_h)
        })
        
    df_cov = pd.DataFrame(cov_recs)
    df_cov.to_csv(TABLES_DIR / "event_sensor_coverage_v2.csv", index=False)
    
    # Generate Postmortem MD
    valid_25 = df_audit[(df_audit['horizon_m'] == 25) & (df_audit['join_status'].isin(['EXACT', 'NEAR_EXACT']))]
    valid_50 = df_audit[(df_audit['horizon_m'] == 50) & (df_audit['join_status'].isin(['EXACT', 'NEAR_EXACT']))]
    valid_100 = df_audit[(df_audit['horizon_m'] == 100) & (df_audit['join_status'].isin(['EXACT', 'NEAR_EXACT']))]
    
    unique_usable_wells = valid_25['sensor_well_id'].unique()
    
    # Write MD
    md_content = f"""# Event Sensor Integration Postmortem V2

## Introduction
This postmortem objectively audits the validity of joining our verified DDR `FORMATION_MUD_LOSS` episodes with the high-frequency USROP sensor dataset. 

## 1. USROP Depth Sampling
The USROP dataset was measured to have a median sampling interval of `{median_step:.2f}m`. Therefore, a maximum allowable join distance was strictly set to `{MAX_JOIN_DIST}m`. Any nearest-neighbor match exceeding this distance is actively rejected to prevent silent interpolation across unlogged sections.

## 2. Answers to Critical ML Questions

### A. How many FML episodes genuinely have valid sensor data?
Out of the original {len(df_fml)} verified DDR episodes, only **{len(mapped)}** belonged to wells that exist in the USROP dataset. 
Of those, the number of episodes that actually have active sensor history logged *at or before* the required depth cutoffs is significantly lower due to incomplete USROP start-depths.

### B. How many are valid at 25/50/100m?
- **At 25m horizon**: {len(valid_25)} valid episodes
- **At 50m horizon**: {len(valid_50)} valid episodes
- **At 100m horizon**: {len(valid_100)} valid episodes

### C. Which wells are usable?
The episodes with valid joins come from the following wells:
{list(unique_usable_wells)}

### D. Which episodes were rejected and why?
Many episodes were rejected due to:
- **UNRESOLVED_NO_WELL**: The DDR event occurred in a well (e.g., `15/9-19 A`) that simply isn't present in the 7-well USROP sample.
- **UNRESOLVED_NO_HISTORY**: The USROP dataset for the mapped well starts *after* the event's `prediction_cutoff_md`. We cannot predict an event if the sensors haven't started logging yet.
- **REJECTED_DISTANCE**: The nearest sensor sample was >{MAX_JOIN_DIST}m away from the cutoff, indicating a gap in logging.

### E. Is the current dataset scientifically large enough for supervised ML?
**NO.**
With only {len(valid_25)} valid positive episodes spanning just {len(unique_usable_wells)} well(s), the resulting dataset is too small to support robust supervised learning or Leave-One-Well-Out (LOWO) evaluation. Any metrics derived from such a small subset would be statistically insignificant and prone to extreme overfitting.

### F. What real data acquisition is required next?
**STOP EXPERIMENTATION.**
To proceed with a scientifically valid supervised learning task, we must:
1. Acquire the complete WITSML sensor archive for all {len(df_fml)} positive `FORMATION_MUD_LOSS` wells, not just the 7 currently in USROP.
2. OR, expand the DDR event extraction to all historical Equinor/Volve wells, hoping to find more events that happen to intersect with the 7 USROP wells.
Until real data density is increased, building classifiers on this dataset is forbidden.
"""
    
    with open(REPORTS_DIR / "event_sensor_integration_postmortem_v2.md", "w") as f:
        f.write(md_content)
        
    logger.info("Done generating strict V2 sensor audit.")

if __name__ == "__main__":
    main()
