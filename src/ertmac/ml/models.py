import pandas as pd
import numpy as np
from typing import List, Dict, Any

class BaseRiskModel:
    def fit(self, X: pd.DataFrame, y: pd.Series):
        raise NotImplementedError
        
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError

class PersistenceBaseline(BaseRiskModel):
    """
    Naive baseline: If the recent state resembles historical risk, predict 1.
    Often acts as a proxy for 'has a minor anomaly already started'.
    """
    def __init__(self, target_channel: str = 'rop_delta_5m', threshold: float = -10.0):
        self.target_channel = target_channel
        self.threshold = threshold
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        pass # No training required
        
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        import numpy as np
        if self.target_channel in X.columns:
            probs = np.where(X[self.target_channel] < self.threshold, 0.8, 0.1)
            return probs
        return np.zeros(len(X))

class LogisticRegressionBaseline(BaseRiskModel):
    """
    Linear baseline for interpretable coefficient analysis.
    """
    def __init__(self):
        # We don't import sklearn here to avoid heavy dependencies if not needed yet,
        # but the interface is ready.
        self.model = None
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        raise RuntimeError("ML Training is explicitly blocked until real data arrives.")

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        raise RuntimeError("ML Training is explicitly blocked until real data arrives.")

class TreeBaseline(BaseRiskModel):
    """
    Non-linear baseline (LightGBM/XGBoost).
    """
    def __init__(self, backend='lightgbm'):
        self.backend = backend
        self.model = None
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        raise RuntimeError("ML Training is explicitly blocked until real data arrives.")
        
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        raise RuntimeError("ML Training is explicitly blocked until real data arrives.")
