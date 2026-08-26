from dataclasses import dataclass
from typing import Optional

@dataclass
class MLPipelineConfig:
    """
    Strict scientific boundaries for predictive risk modeling.
    """
    # Prediction Parameters
    prediction_horizon_m: float = 25.0
    secondary_horizons_m: tuple = (50.0, 100.0)
    
    # Negative Sampling
    event_exclusion_buffer_m: float = 50.0
    
    # Training Requirements
    min_independent_positive_well_groups: int = 5
    evaluation_strategy: str = "Leave-One-Well-Out (LOWO)"
    
    # Leakage Prevention Flags
    allow_post_onset_features: bool = False
    allow_event_text_features: bool = False
    allow_mitigation_leakage: bool = False

    def validate_dataset_readiness(self, num_independent_positive_groups: int) -> bool:
        """
        Hard block on ML training if the real dataset is insufficient.
        """
        if num_independent_positive_groups < self.min_independent_positive_well_groups:
            raise ValueError(
                f"ML BLOCKED: Found {num_independent_positive_groups} independent positive well groups. "
                f"Minimum required is {self.min_independent_positive_well_groups} for robust LOWO evaluation."
            )
        return True

def causal_feature_cutoff(onset_md: float, horizon: float) -> float:
    """
    Calculates the strict measured depth boundary.
    No sensor data > cutoff may enter the feature payload.
    """
    return onset_md - horizon
