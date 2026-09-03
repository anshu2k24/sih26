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
            self.available_wells = []

        # Load well coordinates metadata via GeospatialIntelligence (Supabase-first)
        self.coords_metadata = {}
        try:
            from ertmac.nwis.geospatial import GeospatialIntelligence
            geo = GeospatialIntelligence()
            self.coords_metadata = geo.coords
        except Exception as e:
            logger.warning(f"Could not load well metadata: {e}")

        # If source had no records loaded yet, derive available wells from wellbores metadata
        if not self.available_wells and self.coords_metadata:
            self.available_wells = list(self.coords_metadata.keys())
        elif not self.available_wells:
            self.available_wells = ["15/9-F-15", "15/9-F-14", "15/9-F-9 A", "15/9-F-9", "15/9-F-7", "15/9-F-5", "15/9-F-15S"]

        self._lock = threading.Lock()

    def get_available_wells(self) -> List[Dict[str, Any]]:
        if not self.coords_metadata:
            try:
                from ertmac.nwis.geospatial import GeospatialIntelligence
                self.coords_metadata = GeospatialIntelligence().coords
            except Exception:
                pass

        # Return all known wells from geospatial metadata and known Volve wellbores
        known_wells = set(self.coords_metadata.keys()) if self.coords_metadata else set()
        if hasattr(self, "available_wells") and self.available_wells:
            known_wells.update(self.available_wells)

        if not known_wells:
            known_wells = {"15/9-F-15", "15/9-F-14", "15/9-F-9 A", "15/9-F-9", "15/9-F-7", "15/9-F-5", "15/9-F-4", "15/9-F-1", "15/9-F-12", "15/9-F-11", "15/9-F-10", "15/9-F-15S"}

        results = []
        for w in sorted(known_wells):
            meta = self.coords_metadata.get(w, {})
            item = {
                "well_id": w,
                "status": meta.get("status", "available"),
                "name": meta.get("name", f"Well {w}"),
                "field": meta.get("field", "Volve"),
                "operator": meta.get("operator", "Equinor"),
                "latitude": meta.get("latitude"),
                "longitude": meta.get("longitude"),
                "water_depth_m": meta.get("water_depth_m", 84.0),
                "slot_name": meta.get("slot_name")
            }
            results.append(item)
        return results

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

    def send_stream_command(self, action: str, **kwargs) -> Dict[str, Any]:
        """Dispatches an interactive stream control command (start, pause, resume) to the sensor stream."""
        return self.stream_client.send_command(action, **kwargs)

    def get_stream_status(self) -> Dict[str, Any]:
        """Returns the current sensor stream run status and drilling parameters."""
        st = self.stream_client.get_state()
        return {
            "is_streaming": st.get("is_streaming", False),
            "status": st.get("status", "STREAM DISCONNECTED"),
            "well_id": st.get("well_id", "15/9-F-15"),
            "current_md": st.get("current_md", 0.0),
            "samples_received": st.get("samples_received", 0),
        }


# Global Singleton Application State
_app_state_instance: Optional[ApplicationStateManager] = None

def get_app_state() -> ApplicationStateManager:
    global _app_state_instance
    if _app_state_instance is None:
        _app_state_instance = ApplicationStateManager()
    return _app_state_instance
