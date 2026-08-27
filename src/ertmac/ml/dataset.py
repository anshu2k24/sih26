import pandas as pd
import numpy as np

def generate_deterministic_negatives(
    df_sensors: pd.DataFrame, 
    df_events: pd.DataFrame, 
    target_event_type: str,
    ratio: int = 5,
    random_seed: int = 42,
    exclusion_zone_m: float = 50.0
) -> pd.DataFrame:
    """
    Generates negative samples deterministically.
    - Excludes +/- 50m around every positive onset.
    - Only samples valid drilling telemetry.
    - Avoids duplicate samples.
    - Preserves well/group identity.
    - Uses fixed seed.
    """
    np.random.seed(random_seed)
    
    # 1. Identify all positive event depths per wellbore
    pos_events = df_events[df_events['event_type'] == target_event_type].copy()
    
    exclusion_zones = {}
    for _, row in pos_events.iterrows():
        wb = row['wellbore_id']
        onset = row['md']
        if pd.isnull(onset):
            continue
        if wb not in exclusion_zones:
            exclusion_zones[wb] = []
        exclusion_zones[wb].append((onset - exclusion_zone_m, onset + exclusion_zone_m))
        
    # 2. Filter sensors to find valid negative candidates
    # A candidate is valid if it falls outside all exclusion zones for its wellbore
    # and has valid MD.
    candidates = df_sensors.dropna(subset=['md']).copy()
    
    def is_valid_negative(row):
        wb = row['wellbore_id']
        md = row['md']
        if wb in exclusion_zones:
            for (start, end) in exclusion_zones[wb]:
                if start <= md <= end:
                    return False
        return True
        
    candidates['is_valid'] = candidates.apply(is_valid_negative, axis=1)
    valid_candidates = candidates[candidates['is_valid'] == True].copy()
    
    # 3. Sample
    negatives = []
    
    for wb, group_df in valid_candidates.groupby('wellbore_id'):
        # Find how many positives this wellbore had to balance per-wellbore if possible
        # Actually, global ratio or per-wellbore ratio? Let's do per-wellbore ratio
        num_pos = len(pos_events[pos_events['wellbore_id'] == wb])
        num_neg_to_sample = num_pos * ratio
        
        # If it has 0 positives, we might still want to sample from it to provide "safe" wells.
        # But for now, if it has 0 positives, let's just sample a default number or ratio of its size.
        if num_pos == 0:
            num_neg_to_sample = max(10, len(group_df) // 100) 
            
        num_neg_to_sample = min(num_neg_to_sample, len(group_df))
        
        if num_neg_to_sample > 0:
            sampled = group_df.sample(n=num_neg_to_sample, random_state=random_seed, replace=False)
            negatives.append(sampled)
            
    if not negatives:
        return pd.DataFrame(columns=candidates.columns)
        
    df_neg = pd.concat(negatives, ignore_index=True)
    df_neg['is_event'] = 0
    df_neg = df_neg.drop(columns=['is_valid'])
    
    return df_neg
