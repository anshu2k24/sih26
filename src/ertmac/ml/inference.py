from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

@dataclass
class InferenceInput:
    well_id: str
    timestamp: str
    md: float
    tvd: float
    rop: float
    wob: float
    rpm: float
    torque: float
    hookload: float
    spp: float
    flow_in: float
    mud_density: float

@dataclass
class InferenceOutput:
    current_md: float
    prediction_horizon: float
    model_version: str
    risk_score: Optional[float]
    alert_state: str  # e.g., SAFE, WARNING, CRITICAL, NO_PREDICTION, SHADOW_FEATURES_ONLY
    top_contributing_features: Dict[str, float]
    data_quality_status: str
    provenance_timestamp: str

class PreprocessingStrategy:
    RAW = "RAW"  # Use basic causal stats without external train-fold scaling
    GLOBAL_STANDARDIZED = "GLOBAL_STANDARDIZED"  # Fit on training wells only, apply to inference
    RELATIVE_DELTA = "RELATIVE_DELTA"  # Express inputs strictly as relative changes/slopes over a window

class DataQualityGate:
    def __init__(self, required_history_md=25.0, max_gap_md=10.0):
        self.required_history_md = required_history_md
        self.max_gap_md = max_gap_md
        
    def check_quality(self, history_df: pd.DataFrame, current_md: float, wellbore_id: str) -> str:
        """
        Validates causal data integrity before ANY prediction is allowed.
        """
        if history_df.empty:
            return "FAIL_EMPTY_HISTORY"
            
        # 1. Well Identity Verification
        if (history_df['wellbore_id'] != wellbore_id).any():
            return "FAIL_MIXED_WELLS"
            
        # 2. Required Channels
        required = ['md', 'rop', 'wob', 'rpm', 'torque', 'hookload', 'spp', 'flow_in', 'mud_density']
        for req in required:
            if req not in history_df.columns:
                return f"FAIL_MISSING_CHANNEL_{req.upper()}"
                
        # 3. Sentinel and Impossible Values
        # Ensure -999.25 or negative depth isn't present
        numeric_cols = [c for c in required if c != 'md']
        if history_df[numeric_cols].isin([-999.25, -999.0]).any().any():
            return "FAIL_SENTINEL_VALUES"
        if (history_df['md'] < 0).any():
            return "FAIL_NEGATIVE_MD"
            
        # 4. Future Row Leakage
        if (history_df['md'] > current_md).any():
            return "FAIL_FUTURE_ROWS"
            
        # 5. Insufficient History
        min_md = history_df['md'].min()
        if (current_md - min_md) < self.required_history_md:
            return "FAIL_INSUFFICIENT_HISTORY"
            
        # 6. Excessive Gaps
        history_df = history_df.sort_values('md')
        causal_window_start = current_md - self.required_history_md
        causal_window = history_df[history_df['md'] >= causal_window_start]
        gaps = causal_window['md'].diff().max()
        if pd.notna(gaps) and gaps > self.max_gap_md:
            return "FAIL_EXCESSIVE_GAPS"
            
        return "PASS"

class ShadowInferenceRunner:
    """
    Shadow inference runner to process historical/replayed data (e.g. Volve)
    without triggering real-world actions, exclusively for ML testing.
    """
    def __init__(self, model=None, strategy=PreprocessingStrategy.RAW, horizon=25.0):
        self.model = model
        self.strategy = strategy
        self.horizon = horizon
        self.gate = DataQualityGate(required_history_md=25.0)
        
    def process_stream(self, history_df: pd.DataFrame, current_md: float, well_id: str, timestamp: str) -> InferenceOutput:
        """
        Processes a sliding window of historical sensor records.
        """
        status = self.gate.check_quality(history_df, current_md, well_id)
        
        if status != "PASS":
            return InferenceOutput(
                current_md=current_md,
                prediction_horizon=self.horizon,
                model_version="shadow_v1",
                risk_score=None,
                alert_state="NO_PREDICTION",
                top_contributing_features={},
                data_quality_status=status,
                provenance_timestamp=timestamp
            )
            
        # Execute causal feature extraction natively
        from ertmac.ml.features import construct_causal_features, CausalFeatureConfig
        features = construct_causal_features(history_df, current_md, CausalFeatureConfig())
        
        if not features:
            return InferenceOutput(
                current_md=current_md,
                prediction_horizon=self.horizon,
                model_version="shadow_v1",
                risk_score=None,
                alert_state="NO_PREDICTION",
                top_contributing_features={},
                data_quality_status="FAIL_FEATURE_EXTRACTION",
                provenance_timestamp=timestamp
            )
            
        # If no model is available, simply expose features as a payload
        if self.model is None:
            return InferenceOutput(
                current_md=current_md,
                prediction_horizon=self.horizon,
                model_version="shadow_v1_no_model",
                risk_score=None,
                alert_state="SHADOW_FEATURES_ONLY",
                top_contributing_features=features,
                data_quality_status="PASS",
                provenance_timestamp=timestamp
            )
            
        # Future: Execute preprocessed inference (requires locked standardization/deltas)
        # return model_prediction_output
        pass
