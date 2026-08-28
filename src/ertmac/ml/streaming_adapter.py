import logging
from typing import Dict, Any, Optional, Union, List
import pandas as pd
import numpy as np

from ertmac.streaming.schemas import CausalStreamBuffer, SensorRecord
from ertmac.ml.features import construct_causal_features, CausalFeatureConfig
from ertmac.ml.ingestion import IngestionValidator
from ertmac.ml.contracts import MLPipelineConfig
from ertmac.ml.models import BaseModel

logger = logging.getLogger("StreamInferenceAdapter")


class StreamInferenceAdapter:
    """
    Source-Agnostic Stream Inference Adapter.
    Connects CausalStreamBuffer -> Existing Feature Builder -> Existing ML Inference.

    Guarantees:
    - Consumes ONLY emitted causal records up to current stream position.
    - Zero future-data leakage (MD <= cutoff_md, t <= current timestamp).
    - Preserves existing ML readiness gates without weakening or bypass.
    - Exposes structured ML_NOT_READY status when ML is blocked by gate checks.
    """
    def __init__(
        self,
        feature_config: Optional[CausalFeatureConfig] = None,
        model: Optional[BaseModel] = None,
        events_df: Optional[pd.DataFrame] = None
    ):
        self.feature_config = feature_config if feature_config is not None else CausalFeatureConfig()
        self.model = model
        self.events_df = events_df
        self.validator = IngestionValidator()
        self.pipeline_config = MLPipelineConfig()

    def check_ml_readiness(self, sensor_df: pd.DataFrame) -> tuple[bool, str, dict]:
        """
        Evaluates the existing ML readiness gate on provided dataset.
        """
        if self.events_df is None or len(self.events_df) == 0:
            from pathlib import Path
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            ver_path = repo_root / "reports" / "tables" / "verified_event_episodes_v2.csv"
            if ver_path.exists():
                self.events_df = pd.read_csv(ver_path)
            else:
                return False, "ML_BLOCKED: Verified event episodes table missing for LOWO gate validation.", {}

        if len(sensor_df) == 0:
            return False, "ML_BLOCKED: Zero sensor telemetry provided for gate validation.", {}

        return self.validator.check_readiness(self.events_df, sensor_df)

    def process_causal_position(
        self,
        buffer_or_records: Union[CausalStreamBuffer, pd.DataFrame, List[Dict[str, Any]], List[SensorRecord]],
        cutoff_md: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Processes current stream position strictly using causal history <= cutoff_md.
        """
        well_id = "UNKNOWN"
        current_md = 0.0
        emitted_count = 0

        if isinstance(buffer_or_records, CausalStreamBuffer):
            well_id = buffer_or_records.state.well_id
            current_md = buffer_or_records.state.current_md
            emitted_count = buffer_or_records.state.emitted_count
            if cutoff_md is None:
                cutoff_md = current_md
            causal_records = buffer_or_records.get_history_at_cutoff(cutoff_md)
            if not causal_records:
                return {
                    "status": "NO_TELEMETRY",
                    "is_blocked": True,
                    "gate_reason": f"No causal sensor history available before MD {cutoff_md}m.",
                    "cutoff_md": cutoff_md,
                    "well_id": well_id,
                    "risk_score": None,
                    "features": {}
                }
            df_causal = pd.DataFrame([r.to_dict() for r in causal_records])
        elif isinstance(buffer_or_records, pd.DataFrame):
            df_all = buffer_or_records.copy()
            if len(df_all) == 0:
                return {
                    "status": "NO_TELEMETRY",
                    "is_blocked": True,
                    "gate_reason": "Empty telemetry dataframe provided.",
                    "cutoff_md": cutoff_md or 0.0,
                    "well_id": well_id,
                    "risk_score": None,
                    "features": {}
                }
            if cutoff_md is None:
                cutoff_md = float(df_all["md"].max())
            df_causal = df_all[df_all["md"] <= cutoff_md].copy()
            well_id = str(df_causal["well_id"].iloc[-1]) if "well_id" in df_causal.columns and len(df_causal) > 0 else "UNKNOWN"
            current_md = float(df_causal["md"].max()) if len(df_causal) > 0 else 0.0
            emitted_count = len(df_causal)
        elif isinstance(buffer_or_records, list):
            if not buffer_or_records:
                return {
                    "status": "NO_TELEMETRY",
                    "is_blocked": True,
                    "gate_reason": "Empty records list provided.",
                    "cutoff_md": cutoff_md or 0.0,
                    "well_id": well_id,
                    "risk_score": None,
                    "features": {}
                }
            dicts = []
            for item in buffer_or_records:
                if isinstance(item, SensorRecord):
                    dicts.append(item.to_dict())
                elif isinstance(item, dict):
                    dicts.append(item)
            df_all = pd.DataFrame(dicts)
            if cutoff_md is None:
                cutoff_md = float(df_all["md"].max())
            df_causal = df_all[df_all["md"] <= cutoff_md].copy()
            well_id = str(df_causal["well_id"].iloc[-1]) if "well_id" in df_causal.columns and len(df_causal) > 0 else "UNKNOWN"
            current_md = float(df_causal["md"].max()) if len(df_causal) > 0 else 0.0
            emitted_count = len(df_causal)
        else:
            raise TypeError(f"Unsupported buffer/records type: {type(buffer_or_records)}")

        if len(df_causal) == 0:
            return {
                "status": "NO_TELEMETRY",
                "is_blocked": True,
                "gate_reason": f"No causal sensor history available before MD {cutoff_md}m.",
                "cutoff_md": cutoff_md,
                "well_id": well_id,
                "risk_score": None,
                "features": {}
            }

        # STRICT LEAKAGE ASSERTION: No future records in df_causal
        assert (df_causal["md"] > cutoff_md).sum() == 0, (
            f"Leakage Violation: Future records with MD > {cutoff_md} found in causal DataFrame!"
        )

        # 2. Run existing Feature Builder (construct_causal_features)
        try:
            feature_dict = construct_causal_features(df_causal, cutoff_md, self.feature_config)
        except ValueError as ve:
            return {
                "status": "FEATURE_BUILD_ERROR",
                "is_blocked": True,
                "gate_reason": str(ve),
                "cutoff_md": cutoff_md,
                "well_id": well_id,
                "risk_score": None,
                "features": {}
            }

        # 3. Evaluate existing ML Readiness Gate
        is_ready, gate_msg, gate_stats = self.check_ml_readiness(df_causal)

        # 4. If ML readiness gate blocks inference OR no trained model exists
        if not is_ready or self.model is None:
            return {
                "status": "ML_NOT_READY",
                "is_blocked": True,
                "gate_reason": gate_msg,
                "gate_stats": gate_stats,
                "cutoff_md": cutoff_md,
                "well_id": well_id,
                "current_md": current_md,
                "emitted_count": emitted_count,
                "risk_score": None,  # NEVER fabricate predictions when blocked
                "features": feature_dict
            }

        # 5. If ML is legitimately ready & trained model exists: execute online inference
        df_features_single = pd.DataFrame([feature_dict])
        feature_cols = [c for c in df_features_single.columns if not pd.isna(df_features_single[c].iloc[0])]

        try:
            prob = float(self.model.predict_proba(df_features_single[feature_cols])[0])
            return {
                "status": "SUCCESS",
                "is_blocked": False,
                "gate_reason": "ML Pipeline Active",
                "cutoff_md": cutoff_md,
                "well_id": well_id,
                "current_md": current_md,
                "emitted_count": emitted_count,
                "risk_score": prob,
                "features": feature_dict
            }
        except Exception as e:
            return {
                "status": "INFERENCE_ERROR",
                "is_blocked": True,
                "gate_reason": f"Inference execution failed: {e}",
                "cutoff_md": cutoff_md,
                "well_id": well_id,
                "risk_score": None,
                "features": feature_dict
            }
