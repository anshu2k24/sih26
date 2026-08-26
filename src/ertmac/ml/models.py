from typing import Dict
import pandas as pd
import numpy as np

class BaseModel:
    def fit(self, X: pd.DataFrame, y: pd.Series):
        raise NotImplementedError
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError

class PersistenceBaseline(BaseModel):
    """
    Naive baseline: predicts the prevalence of the training set for all test samples.
    """
    def __init__(self):
        self.prevalence = 0.0
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.prevalence = float(y.mean())
        
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return np.full((len(X),), self.prevalence)

class LogisticRegressionBaseline(BaseModel):
    def __init__(self):
        try:
            from sklearn.linear_model import LogisticRegression
            self.model = LogisticRegression(max_iter=1000, class_weight='balanced')
        except ImportError:
            self.model = None

    def fit(self, X: pd.DataFrame, y: pd.Series):
        if self.model is None:
            raise ImportError("scikit-learn not installed")
        # Handle nans safely (simplistic fill for baseline)
        X_fill = X.fillna(X.mean()).fillna(0)
        self.model.fit(X_fill, y)
        
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        X_fill = X.fillna(X.mean()).fillna(0)
        return self.model.predict_proba(X_fill)[:, 1]

class LightGBMBaseline(BaseModel):
    def __init__(self):
        try:
            from lightgbm import LGBMClassifier
            self.model = LGBMClassifier(n_estimators=100, class_weight='balanced', random_state=42)
        except ImportError:
            self.model = None
            
    def fit(self, X: pd.DataFrame, y: pd.Series):
        if self.model is None:
            raise ImportError("lightgbm not installed")
        self.model.fit(X, y)
        
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]
