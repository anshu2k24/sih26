import pandas as pd
import numpy as np
from pathlib import Path
import json

def calculate_structural_validity(df_events: pd.DataFrame, df_sensors: pd.DataFrame) -> dict:
    # Schema Contract (10 pts)
    required_sensors = {"well_id", "timestamp", "md", "rop", "wob", "rpm", "torque", "hookload", "spp", "flow_in", "mud_density"}
    required_events = {"well_id", "wellbore_id", "independent_well_group", "timestamp", "md", "event_type"}
    
    sensor_schema_ok = required_sensors.issubset(df_sensors.columns)
    event_schema_ok = required_events.issubset(df_events.columns)
    
    schema_score = 10.0 if (sensor_schema_ok and event_schema_ok) else 0.0
    
    # Causal/Leakage Integrity (10 pts)
    # Check that events have onset MD and timestamps
    causal_score = 10.0
    if df_events['md'].isnull().any():
        causal_score -= 5.0
    
    # LOWO/Well Diversity (10 pts)
    num_wells = df_sensors['well_id'].nunique()
    num_independent = df_events['independent_well_group'].nunique() if not df_events.empty else 0
    diversity_score = min(10.0, num_wells * 1.0 + num_independent * 1.0) # max 10
    if num_independent < 5:
        diversity_score -= 5.0
        
    return {
        "Schema Contract": schema_score,
        "Causal/Leakage Integrity": max(0.0, causal_score),
        "LOWO/Well Diversity": max(0.0, diversity_score)
    }

def calculate_physical_plausibility(df_sensors: pd.DataFrame) -> dict:
    # Range Plausibility (20 pts)
    range_score = 20.0
    
    # Negative checks
    for col in ["rop", "wob", "rpm", "spp", "flow_in"]:
        if (df_sensors[col] < 0).any():
            range_score -= 2.0
            
    # Impossible physics (e.g. mud density < 0.5 or > 3.0)
    if (df_sensors['mud_density'] < 0.8).any() or (df_sensors['mud_density'] > 3.0).any():
        range_score -= 5.0
        
    # Temporal/Depth Continuity (20 pts)
    continuity_score = 20.0
    for wid, grp in df_sensors.groupby("well_id"):
        if not grp['md'].is_monotonic_increasing:
            continuity_score -= 5.0
            break
            
    for wid, grp in df_sensors.groupby("well_id"):
        if not grp['timestamp'].is_monotonic_increasing:
            continuity_score -= 5.0
            break
            
    return {
        "Range Plausibility": max(0.0, range_score),
        "Temporal/Depth Continuity": max(0.0, continuity_score)
    }

def calculate_statistical_realism(df_events: pd.DataFrame, df_sensors: pd.DataFrame) -> dict:
    # Cross-channel Correlation (10 pts)
    # ROP and WOB should be somewhat correlated. SPP and flow_in should be strongly correlated.
    corr_score = 10.0
    spp_flow_corr = df_sensors['spp'].corr(df_sensors['flow_in'])
    if abs(spp_flow_corr) < 0.1:
        corr_score -= 5.0 # In our synthetic, they are independent random walks! So this will penalize.
        
    wob_torque_corr = df_sensors['wob'].corr(df_sensors['torque'])
    if abs(wob_torque_corr) < 0.1:
        corr_score -= 5.0
        
    # Event Precursor Realism (10 pts)
    # The current precursor is a PERFECT linear ramp causing ROC-AUC=1.0. 
    # Let's measure if the variance of SPP derivative in the precursor window is unnaturally zero.
    precursor_score = 10.0
    # Our generated data is extremely separable. We penalize heavily for "too clean" behavior.
    # If ROC-AUC=1.0 was seen, it's artificially separable. Since we can't run ML here, we just check standard deviation of the delta.
    df_sensors['spp_diff'] = df_sensors.groupby('well_id')['spp'].diff()
    # Check if we have exact repeating constants (linear drops)
    spp_diff_std = df_sensors['spp_diff'].std()
    mode_count = df_sensors['spp_diff'].round(2).value_counts().max()
    if mode_count > len(df_sensors) * 0.05: # High frequency of the exact same diff means linear ramp
        precursor_score -= 7.0 
    
    # Class Distribution (10 pts)
    class_score = 10.0
    # We want a rare class scenario. If events are > 10% of samples, it's not realistic.
    # Here, events are points, but episodes... let's just say ratio of events to wells.
    if len(df_events) > len(df_sensors['well_id'].unique()) * 5:
        class_score -= 5.0
        
    return {
        "Cross-channel Correlation": max(0.0, corr_score),
        "Event Precursor Realism": max(0.0, precursor_score),
        "Class Distribution Realism": max(0.0, class_score)
    }

def evaluate_quality(df_events: pd.DataFrame, df_sensors: pd.DataFrame) -> pd.DataFrame:
    scores = {}
    scores.update(calculate_structural_validity(df_events, df_sensors))
    scores.update(calculate_physical_plausibility(df_sensors))
    scores.update(calculate_statistical_realism(df_events, df_sensors))
    
    df_scores = pd.DataFrame(list(scores.items()), columns=["Component", "Score"])
    df_scores["Max Score"] = [10, 10, 10, 20, 20, 10, 10, 10]
    
    total = df_scores["Score"].sum()
    return df_scores, total
