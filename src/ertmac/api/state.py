import logging
import threading
from typing import Dict, Any, List, Optional
import pandas as pd

from ertmac.streaming import (
    SensorStreamClient,
    VolveReplaySensorSource,
    SCIENTIFIC_LABEL
)
from ertmac.ml.streaming_adapter import StreamInferenceAdapter

logger = logging.getLogger("ApplicationStateManager")


class ApplicationStateManager:
    """
    Thread-safe Application State Manager for orchestration layer.
    Manages active well streams, current MD, latest telemetry, ML adapter state,
    and historical DDR intelligence queries.
    """
    def __init__(self, sensor_host: str = "localhost", sensor_port: int = 8765):
        self.sensor_host = sensor_host
        self.sensor_port = sensor_port
        self.stream_client = SensorStreamClient(host=sensor_host, port=sensor_port)
        self.stream_client.start()

        # Source for well availability metadata
        try:
            self.source = VolveReplaySensorSource()
            self.available_wells = self.source.get_available_wells()
        except Exception:
            self.available_wells = ["15/9-F-15", "15/9-F-14", "15/9-F-9 A", "15/9-F-9", "15/9-F-7", "15/9-F-5", "15/9-F-15S"]

        self._lock = threading.Lock()

    def get_available_wells(self) -> List[Dict[str, str]]:
        return [{"well_id": w, "status": "available"} for w in self.available_wells]

    def get_well_state(self, well_id: str) -> Dict[str, Any]:
        st = self.stream_client.get_state()
        active_well = st["well_id"] if st["well_id"] != "N/A" else well_id
        return {
            "well_id": active_well,
            "stream_status": st["status"],
            "data_source": SCIENTIFIC_LABEL,
            "current_md": st["current_md"],
            "tvd": st["tvd"],
            "last_timestamp": st["last_timestamp"],
            "samples_received": st["samples_received"],
            "latest_sensor": st["current_record"],
            "ml": {
                "status": st["ml_result"]["status"],
                "is_blocked": st["ml_result"].get("is_blocked", True),
                "gate_reason": st["ml_result"].get("gate_reason", "ML_NOT_READY"),
                "risk_score": st["ml_result"].get("risk_score", None),
                "features_constructed": len(st["ml_result"].get("features", {}))
            }
        }

    def get_latest_sensor(self, well_id: str) -> Optional[Dict[str, Any]]:
        st = self.stream_client.get_state()
        return st["current_record"]

    def get_sensor_history(self, well_id: str, cutoff_md: Optional[float] = None) -> Dict[str, Any]:
        st = self.stream_client.get_state()
        history = st["history"]
        if cutoff_md is None:
            cutoff_md = st["current_md"]

        # STRICT CAUSAL FILTERING: Return ONLY emitted records <= cutoff_md
        causal_records = [r for r in history if r["md"] <= cutoff_md]
        return {
            "well_id": well_id,
            "cutoff_md": cutoff_md,
            "count": len(causal_records),
            "records": causal_records
        }

    def get_risk_status(self, well_id: str) -> Dict[str, Any]:
        st = self.stream_client.get_state()
        ml_res = st["ml_result"]
        return {
            "well_id": well_id,
            "status": ml_res.get("status", "ML_NOT_READY"),
            "is_blocked": ml_res.get("is_blocked", True),
            "risk_score": ml_res.get("risk_score", None),  # NEVER fabricate risk score
            "reason": ml_res.get("gate_reason", "ML Readiness Gate blocked"),
            "features_constructed": len(ml_res.get("features", {}))
        }


# Global Singleton Application State
_app_state_instance: Optional[ApplicationStateManager] = None

def get_app_state() -> ApplicationStateManager:
    global _app_state_instance
    if _app_state_instance is None:
        _app_state_instance = ApplicationStateManager()
    return _app_state_instance
