import pandas as pd

def check_feature_leakage(df_features: pd.DataFrame):
    """
    Strict validation to ensure no future information or text is present.
    """
    forbidden_keywords = ['text', 'evidence', 'mitigation', 'resolution', 'label', 'target', 'event_type', 'onset_md']
    
    for col in df_features.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in forbidden_keywords):
            raise ValueError(f"CRITICAL LEAKAGE DETECTED: Column '{col}' contains forbidden information.")

def validate_causal_contract(onset_md: float, feature_mds: pd.Series, horizon: float):
    """
    Ensures all sensor readings used to predict an event strictly obey the horizon.
    """
    cutoff = onset_md - horizon
    if (feature_mds > cutoff).any():
        raise ValueError(f"CRITICAL LEAKAGE DETECTED: Features contain data beyond cutoff {cutoff}")

def check_overlap(train_wells: set, test_wells: set):
    """
    Ensures LOWO integrity.
    """
    overlap = train_wells.intersection(test_wells)
    if overlap:
        raise ValueError(f"LOWO INTEGRITY VIOLATION: Wells {overlap} appear in both train and test folds.")
