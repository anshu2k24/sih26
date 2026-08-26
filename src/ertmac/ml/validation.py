import numpy as np
import pandas as pd
from typing import Dict

def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, float]:
    """
    Computes standard binary classification metrics.
    """
    try:
        from sklearn.metrics import roc_auc_score, average_precision_score, confusion_matrix, precision_recall_fscore_support
    except ImportError:
        return {}
        
    y_pred = (y_prob >= threshold).astype(int)
    
    if len(np.unique(y_true)) == 1:
        roc_auc = np.nan
        pr_auc = np.nan
    else:
        roc_auc = float(roc_auc_score(y_true, y_prob))
        pr_auc = float(average_precision_score(y_true, y_prob))
        
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary', zero_division=0)
    
    tn, fp, fn, tp = 0, 0, 0, 0
    if len(np.unique(y_true)) > 1 or (len(np.unique(y_true)) == 1 and y_true[0] == 0):
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
    elif len(np.unique(y_true)) == 1 and y_true[0] == 1:
        tp = int(np.sum(y_pred == 1))
        fn = int(np.sum(y_pred == 0))
    
    return {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn)
    }

def check_feature_leakage(df: pd.DataFrame):
    # Detect obviously leaky columns
    leaky_cols = [c for c in df.columns if 'mitigation' in c.lower() or 'event_text' in c.lower()]
    if leaky_cols:
        raise ValueError(f"CRITICAL LEAKAGE DETECTED: Found forbidden columns {leaky_cols}")

def validate_causal_contract(onset_md, cutoff_md, sensor_md):
    if sensor_md > cutoff_md:
        raise ValueError("Future data leakage.")

def check_overlap(train_wells: set, test_wells: set):
    if train_wells.intersection(test_wells):
        raise ValueError("LOWO INTEGRITY VIOLATION: Train and test wells overlap.")
