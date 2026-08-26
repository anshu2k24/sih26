from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime

# =============================================================================
# DATA ACQUISITION CONTRACTS
# These dataclasses define the strict schemas expected from OIL/eRTMAC
# before the predictive ML pipeline can resume.
# =============================================================================

@dataclass
class DDREventRecord:
    """
    Contract for raw Daily Drilling Report (DDR) event inputs.
    """
    well_id: str
    wellbore_id: str
    timestamp: datetime
    onset_md: float
    event_type: str
    primary_evidence: str
    mitigation: Optional[str]
    resolution: Optional[str]

@dataclass
class RealtimeSensorRecord:
    """
    Contract for high-frequency eRTMAC/WITSML sensor inputs.
    """
    well_id: str
    wellbore_id: str
    timestamp: datetime
    md: float
    tvd: Optional[float]
    rop: float
    wob: float
    rpm: float
    torque: float
    hookload: float
    spp: float
    flow_in: float
    mud_density: float

# =============================================================================
# ML PIPELINE CONTRACTS
# These parameters strictly bound the causal prediction task.
# =============================================================================

@dataclass
class MLPipelineConfig:
    """
    Strict scientific boundaries for predictive risk modeling.
    """
    # Prediction Parameters
    prediction_horizon_m: float = 25.0
    
    # Negative Sampling
    event_exclusion_buffer_m: float = 50.0
    
    # Training Requirements
    min_positive_wells_required: int = 5
    evaluation_strategy: str = "Leave-One-Well-Out (LOWO)"
    
    # Leakage Prevention Flags
    allow_post_onset_features: bool = False
    allow_event_text_features: bool = False
    allow_mitigation_leakage: bool = False

    def validate_dataset_readiness(self, num_positive_wells: int) -> bool:
        """
        Hard block on ML training if the real dataset is insufficient.
        """
        if num_positive_wells < self.min_positive_wells_required:
            raise ValueError(
                f"ML BLOCKED: Found {num_positive_wells} positive wells. "
                f"Minimum required is {self.min_positive_wells_required} for robust LOWO evaluation."
            )
        return True

def causal_feature_cutoff(onset_md: float, horizon: float) -> float:
    """
    Calculates the strict measured depth boundary.
    No sensor data > cutoff may enter the feature payload.
    """
    return onset_md - horizon
