import json
import time
import threading
import logging
from collections import deque
from typing import Dict, Any, List, Optional
import pandas as pd

import websockets
import asyncio

from ertmac.streaming.schemas import SensorRecord, SCIENTIFIC_LABEL
from ertmac.ml.streaming_adapter import StreamInferenceAdapter

logger = logging.getLogger("SensorStreamClient")


class SensorStreamClient:
    """
    Thread-safe WebSocket Client connecting to live sensor stream (ws://host:port).
    Maintains real-time stream state, causal telemetry history, and evaluates ML inference adapter.
    Handles disconnect and automatic reconnect without crashing application.
    """
    def __init__(self, host: str = "localhost", port: int = 8765, max_history: int = 2000):
        self.host = host
        self.port = port
        self.uri = f"ws://{host}:{port}"
        self.max_history = max_history

        self.status = "STREAM DISCONNECTED"
        self.is_streaming = False
        self.well_id = ""
        self.current_md = 0.0
        self.tvd: Optional[float] = None
        self.last_timestamp = "N/A"
        self.samples_received = 0
        self.current_record: Optional[Dict[str, Any]] = None
        self.history: deque = deque(maxlen=max_history)

        import joblib
        import os
        import numpy as np
        from ertmac.ml.models import BaseModel
        
        class IsoForestWrapper(BaseModel):
            def __init__(self, model_path, features_path):
                self.model = joblib.load(model_path)
                self.features = joblib.load(features_path)
                # Calibrated 98th-percentile anomaly threshold for Volve formation
                self.anomaly_threshold = 0.088
            
            def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
                df = X.copy()
                for col in self.features:
                    if col not in df.columns:
                        df[col] = 0.0
                df = df[self.features].fillna(0.0)
                # Isolation Forest continuous decision function (higher = more anomalous)
                scores = -self.model.decision_function(df)
                probs = np.where(scores >= self.anomaly_threshold, 1.0, 0.0)
                return probs

        try:
            iso_model = IsoForestWrapper(
                'ml_prediction_dir/saved_models/volve_iso_forest.joblib',
                'ml_prediction_dir/saved_models/volve_iso_features.joblib'
            )
        except Exception as e:
            logger.error(f"Could not load IsoForest model: {e}")
            iso_model = None

        self.ml_adapter = StreamInferenceAdapter(model=iso_model)
        self.ml_result: Dict[str, Any] = {
            "status": "ML_NOT_READY",
            "is_blocked": True,
            "gate_reason": "Stream disconnected or server offline",
            "risk_score": None,
            "features": {}
        }

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        # Event fired by set_well() to interrupt the in-process streaming loop immediately
        self._well_switch_event = threading.Event()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._connect_and_listen())
        finally:
            loop.close()

    async def _connect_and_listen(self) -> None:
        import os
        use_in_process = os.getenv("STREAM_IN_PROCESS", "false").lower() == "true"

        while self._running:
            if not use_in_process:
                try:
                    logger.debug(f"Connecting to WebSocket stream at {self.uri}...")
                    async with websockets.connect(self.uri, ping_interval=20.0, ping_timeout=20.0) as ws:
                        with self._lock:
                            self.status = "LIVE"
                            self._ws_conn = ws
                            self._loop = asyncio.get_running_loop()
                        logger.info("Connected to sensor stream WebSocket.")

                        async for message in ws:
                            if not self._running:
                                break
                            self._process_message(message)

                except Exception as e:
                    logger.debug(f"Sensor stream disconnected at {self.uri}: {e} (retrying in 2s)...")
                finally:
                    with self._lock:
                        self.status = "STREAM DISCONNECTED"
                        self._ws_conn = None
                        self.ml_result = {
                            "status": "ML_NOT_READY",
                            "is_blocked": True,
                            "gate_reason": "Stream disconnected or server offline",
                            "risk_score": None,
                            "features": {}
                        }
            else:
                # In-process replay fallback for standalone cloud deployment on Render
                try:
                    from ertmac.streaming.sources import VolveReplaySensorSource
                    source = VolveReplaySensorSource()

                    # Determine active well — default to 15/9-F-15 if none set yet
                    with self._lock:
                        active_well = self.well_id if (self.well_id and self.well_id != "N/A") else "15/9-F-15"
                        self.well_id = active_well
                        self.status = "LIVE"
                        # DO NOT force is_streaming=True here — let START DRILLING command control it

                    logger.info(f"In-process stream replay standby for well '{active_well}' (waiting for START command)")
                    current_streaming_well = active_well
                    self._well_switch_event.clear()

                    for rec in source.stream_records(active_well):
                        # Check if runner was stopped or well was switched
                        if not self._running or self._well_switch_event.is_set():
                            break

                        # Honor PAUSE: spin-wait until user sends START/RESUME
                        while not self.is_streaming and self._running and not self._well_switch_event.is_set():
                            time.sleep(0.2)

                        # Re-check after unblocking
                        if not self._running or self._well_switch_event.is_set():
                            break

                        self._process_message(json.dumps(rec.to_dict()))
                        time.sleep(0.1)

                    if self._well_switch_event.is_set():
                        logger.info(f"In-process stream: well switched away from '{active_well}', restarting loop.")
                        self._well_switch_event.clear()
                        # No sleep — restart immediately for new well
                        continue

                except Exception as e:
                    logger.error(f"In-process stream error: {e}")

            if self._running:
                await asyncio.sleep(2.0)

    def _process_message(self, message_str: str) -> None:
        try:
            data = json.loads(message_str)
            if data.get("type") == "STREAM_STATUS" or "is_streaming" in data:
                with self._lock:
                    self.is_streaming = bool(data.get("is_streaming", False))
                return

            if data.get("status") in ("CONNECTED", "STANDBY"):
                with self._lock:
                    self.is_streaming = bool(data.get("is_streaming", False))
                return

            # Gate: if the user has paused, drop incoming telemetry records immediately
            # This stops data from reaching the frontend even if the external simulator keeps running
            with self._lock:
                if not self.is_streaming:
                    return

            rec = SensorRecord.from_dict(data)
            with self._lock:
                # Strictly reject and drop any residual packets from an old well
                if self.well_id and self.well_id != "N/A" and rec.well_id != self.well_id:
                    return

                # Detect well reset or new stream start
                if self.current_md > 0 and rec.md < self.current_md:
                    self.history.clear()
                    self.samples_received = 0

                self.well_id = rec.well_id
                self.current_md = rec.md
                self.tvd = rec.tvd
                self.last_timestamp = rec.timestamp
                self.samples_received += 1
                # NOTE: Do NOT set self.is_streaming = True here.
                # is_streaming is controlled exclusively by send_command() and welcome messages.
                # Setting it here would override a user-initiated pause on every incoming record.
                self.current_record = rec.to_dict()
                self.history.append(rec.to_dict())

                # Evaluate ML adapter on emitted causal history
                df_causal = pd.DataFrame(list(self.history))
                self.ml_result = self.ml_adapter.process_causal_position(
                    buffer_or_records=df_causal, cutoff_md=rec.md
                )
        except Exception as e:
            logger.error(f"Error processing stream message: {e}")

    def send_command(self, action: str, **kwargs) -> Dict[str, Any]:
        """Dispatches an interactive stream control command (start, pause, resume) to the simulator."""
        well_id = kwargs.get("well_id")
        if well_id and well_id != "N/A" and well_id != self.well_id:
            self.set_well(well_id)
        msg = json.dumps({"action": action, **kwargs})
        with self._lock:
            if action in ("start", "resume"):
                self.is_streaming = True
            elif action == "pause":
                self.is_streaming = False

        # Try to forward command to external WS simulator (websockets 13+ compatible)
        ws_conn = getattr(self, "_ws_conn", None)
        loop = getattr(self, "_loop", None)
        if ws_conn is not None and loop is not None and loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(ws_conn.send(msg), loop)
                return {"success": True, "action": action, "dispatched": True}
            except Exception as e:
                logger.warning(f"Failed to dispatch command to stream server: {e}")
        return {"success": True, "action": action, "dispatched": False, "note": "Local state updated"}

    def set_well(self, well_id: str) -> None:
        """Dynamically switches the active well for in-process streaming and causal telemetry."""
        if well_id and well_id != "N/A" and well_id != self.well_id:
            with self._lock:
                self.well_id = well_id
                self.current_md = 0.0
                self.samples_received = 0
                self.history.clear()
                self.current_record = None
                # is_streaming stays whatever it was — START command will set it
                self.ml_result = {
                    "status": "ML_NOT_READY",
                    "is_blocked": True,
                    "gate_reason": f"Initializing stream for well {well_id}...",
                    "risk_score": None,
                    "features": {}
                }
                logger.info(f"Active stream well switched to '{well_id}'")
            # Signal the in-process loop to break out of the old well iterator immediately
            self._well_switch_event.set()

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self.status,
                "is_streaming": self.is_streaming,
                "data_source_label": SCIENTIFIC_LABEL,
                "well_id": self.well_id,
                "current_md": self.current_md,
                "tvd": self.tvd,
                "last_timestamp": self.last_timestamp,
                "samples_received": self.samples_received,
                "current_record": self.current_record,
                "history": list(self.history),
                "ml_result": self.ml_result
            }
