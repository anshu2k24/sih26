#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("build_event_dataset")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
EVENTS_DIR = DATA_PROCESSED / "events"
EVENTS_DIR.mkdir(parents=True, exist_ok=True)

TABLES_DIR = REPO_ROOT / "reports" / "tables"
REPORTS_DIR = REPO_ROOT / "reports"

USROP_PATH = DATA_PROCESSED / "usrop" / "usrop_clean.parquet"
CANDIDATES_PATH = TABLES_DIR / "event_candidates.csv"
VERIFIED_PATH = TABLES_DIR / "verified_event_episodes_v2.csv"
ERRORS_PATH = TABLES_DIR / "event_label_errors.csv"

def main():
    if not VERIFIED_PATH.exists() or not CANDIDATES_PATH.exists():
        logger.error("Required tables not found.")
        return
        
    df_ver = pd.read_csv(VERIFIED_PATH)
    df_cand = pd.read_csv(CANDIDATES_PATH)
    try:
        df_err = pd.read_csv(ERRORS_PATH) if ERRORS_PATH.exists() else pd.DataFrame()
    except Exception:
        df_err = pd.DataFrame()
    
    # ---------------------------------------------------------
    # TASK 1: RECONSTRUCT & VALIDATE EPISODES
    # ---------------------------------------------------------
    logger.info("Task 1: Episode Validation")
    val_records = []
    
    # 1. Uniqueness
    is_unique = df_ver['event_episode_id'].is_unique
    val_records.append({"check": "event_episode_id_uniqueness", "passed": is_unique, "details": "All IDs unique" if is_unique else "Duplicates found"})
    
    # 3 & 4. Onset <= End
    md_valid = df_ver.apply(lambda r: r['onset_md'] <= r['end_md'] if pd.notnull(r['onset_md']) and pd.notnull(r['end_md']) else True, axis=1).all()
    val_records.append({"check": "onset_md_lte_end_md", "passed": md_valid, "details": "Valid"})
    
    # 5. Onset MD not missing
    md_not_missing = df_ver['onset_md'].notnull().all()
    val_records.append({"check": "onset_md_not_missing", "passed": md_not_missing, "details": f"{df_ver['onset_md'].isnull().sum()} missing"})
    
    # 6. verified positive
    is_pos = (df_ver['is_verified_positive'] == True).all()
    val_records.append({"check": "all_verified_positive", "passed": is_pos, "details": "Valid"})
    
    # 8. No rejected labels from ERRORS_PATH
    if len(df_err) > 0:
        err_evidence = df_err['evidence'].values
        no_errs = not df_ver['primary_evidence'].isin(err_evidence).any()
    else:
        no_errs = True
    val_records.append({"check": "no_rejected_errors_included", "passed": no_errs, "details": "Valid"})
    
    df_val = pd.DataFrame(val_records)
    df_val.to_csv(TABLES_DIR / "verified_episode_validation.csv", index=False)
    
    # ---------------------------------------------------------
    # TASK 2: NEGATIVE CLASS SENSITIVITY
    # ---------------------------------------------------------
    logger.info("Task 2: Negative Sampling")
    if USROP_PATH.exists():
        df_usrop = pd.read_parquet(USROP_PATH)
        buffers = [5, 10, 25, 50]
        neg_results = []
        
        for etype in df_ver['event_type'].unique():
            episodes = df_ver[df_ver['event_type'] == etype]
            for buf in buffers:
                # Mask out USROP rows
                valid_mask = np.ones(len(df_usrop), dtype=bool)
                for _, ep in episodes.iterrows():
                    wb = ep['wellbore_id']
                    o_md = ep['onset_md']
                    if pd.isnull(o_md): continue
                    
                    # Exclusion zone: from (onset - buffer) to (onset + buffer)
                    mask = (df_usrop['well_id'] == ep['well_id']) & (df_usrop['Measured Depth m'] >= o_md - buf) & (df_usrop['Measured Depth m'] <= o_md + buf)
                    valid_mask[mask] = False
                    
                total_negatives = valid_mask.sum()
                neg_results.append({
                    "event_type": etype,
                    "buffer_m": buf,
                    "total_valid_negative_samples": total_negatives,
                    "excluded_samples": len(df_usrop) - total_negatives
                })
        df_neg = pd.DataFrame(neg_results)
        df_neg.to_csv(TABLES_DIR / "negative_window_sensitivity.csv", index=False)
        
    # ---------------------------------------------------------
    # TASK 3: PREDICTION HORIZONS
    # ---------------------------------------------------------
    logger.info("Task 3: Horizon Coverage")
    horizons = [5, 10, 25, 50, 100]
    horz_results = []
    
    # Calculate pre-event distance based on available context in USROP or DDR
    # Since USROP has high frequency, the earliest depth for a well is the min depth.
    if USROP_PATH.exists():
        min_depths = df_usrop.groupby('well_id')['Measured Depth m'].min()
        
        for etype in df_ver['event_type'].unique():
            episodes = df_ver[df_ver['event_type'] == etype]
            p_wells = episodes['well_id'].nunique()
            
            for h in horizons:
                suff = 0
                unsuff = 0
                dists = []
                for _, ep in episodes.iterrows():
                    w_id = ep['well_id']
                    o_md = ep['onset_md']
                    if pd.isnull(o_md): continue
                    m_d = min_depths.get(w_id, np.nan)
                    if pd.notnull(m_d):
                        dist = o_md - m_d
                        dists.append(dist)
                        if dist >= h:
                            suff += 1
                        else:
                            unsuff += 1
                
                horz_results.append({
                    "event_type": etype,
                    "horizon_m": h,
                    "positive_episode_count": len(episodes),
                    "positive_wells": p_wells,
                    "episodes_with_sufficient_pre_event_context": suff,
                    "episodes_without_sufficient_context": unsuff,
                    "min_pre_event_distance": np.min(dists) if dists else np.nan,
                    "median_pre_event_distance": np.median(dists) if dists else np.nan
                })
        df_horz = pd.DataFrame(horz_results)
        df_horz.to_csv(TABLES_DIR / "event_horizon_coverage.csv", index=False)
        
    # ---------------------------------------------------------
    # TASK 5: EVENT-CENTERED DDR CONTEXT DATA
    # ---------------------------------------------------------
    logger.info("Task 5: DDR Context Generation")
    
    context_rows = []
    leakage_flags = []
    
    # We use df_cand for context
    df_cand['date'] = pd.to_datetime(df_cand['timestamp_start'].str[:10], errors='coerce')
    
    for _, ep in df_ver.iterrows():
        wb = ep['wellbore_id']
        o_md = ep['onset_md']
        if pd.isnull(o_md): continue
        o_date = pd.to_datetime(ep['onset_timestamp'][:10]) if pd.notnull(ep['onset_timestamp']) else pd.NaT
        
        # All candidates for this wellbore
        cand_wb = df_cand[df_cand['wellbore_id'] == wb].copy()
        
        for _, c_row in cand_wb.iterrows():
            c_md = c_row['md']
            c_date = c_row['date']
            
            role = "UNKNOWN"
            d_to_onset = np.nan
            t_to_onset = np.nan
            
            # Determine causal role based on MD strictly
            if pd.notnull(c_md) and pd.notnull(o_md):
                d_to_onset = o_md - c_md
                if c_md < o_md:
                    role = "PRE_EVENT"
                elif c_md == o_md:
                    role = "ONSET"
                else:
                    role = "POST_EVENT"
            elif pd.notnull(c_date) and pd.notnull(o_date):
                t_to_onset = (o_date - c_date).total_seconds() / 3600.0
                if c_date < o_date:
                    role = "PRE_EVENT"
                elif c_date == o_date:
                    role = "ONSET"
                else:
                    role = "POST_EVENT"
            else:
                continue
                
            # Leakage check for PRE_EVENT
            text_lower = str(c_row['text']).lower()
            if role == "PRE_EVENT":
                # Check explicit target wording
                if ep['event_type'] == "FORMATION_MUD_LOSS" and re.search(r'\b(lost|losses)\b', text_lower) and not re.search(r'\b(no\s+losses)\b', text_lower):
                    leakage_flags.append({
                        "event_episode_id": ep['event_episode_id'],
                        "context_record_id": c_row['event_id'],
                        "leakage_type": "Event Text Leakage",
                        "text": c_row['text'],
                        "reason": "Explicit loss keyword found in pre-event record"
                    })
                # Check mitigation
                if re.search(r'\b(lcm|jarring|worked pipe|acid)\b', text_lower):
                    leakage_flags.append({
                        "event_episode_id": ep['event_episode_id'],
                        "context_record_id": c_row['event_id'],
                        "leakage_type": "Mitigation Leakage",
                        "text": c_row['text'],
                        "reason": "Mitigation action observed before onset MD (possible mislabeled onset or preemptive action)"
                    })
            
            context_rows.append({
                "event_episode_id": ep['event_episode_id'],
                "event_type": ep['event_type'],
                "event_domain": ep['event_domain'],
                "well_id": ep['well_id'],
                "wellbore_id": ep['wellbore_id'],
                "onset_md": o_md,
                "onset_timestamp": ep['onset_timestamp'],
                "context_record_id": c_row['event_id'],
                "context_timestamp": c_row['timestamp_start'],
                "context_md": c_md,
                "context_role": role,
                "raw_code": c_row['raw_code'],
                "raw_text": c_row['text'],
                "distance_to_onset_m": d_to_onset,
                "time_to_onset_hours": t_to_onset
            })
            
    df_ctx = pd.DataFrame(context_rows)
    df_ctx.to_parquet(EVENTS_DIR / "event_context.parquet", index=False)
    
    df_leak = pd.DataFrame(leakage_flags)
    df_leak.to_csv(TABLES_DIR / "event_leakage_flags.csv", index=False)
    
    logger.info("Done building event dataset schema.")

if __name__ == "__main__":
    main()
