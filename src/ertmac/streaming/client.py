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
        self.well_id = "N/A"
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
            
            def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
                df = X.copy()
                for col in self.features:
                    if col not in df.columns:
                        df[col] = 0.0
                df = df[self.features]
                # Isolation Forest predict returns -1 for anomaly, 1 for normal
                preds = self.model.predict(df)
                probs = np.where(preds == -1, 1.0, 0.0)
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
                    wells = source.get_available_wells()
                    active_well = wells[0] if wells else "15/9-F-15"
                    with self._lock:
                        self.status = "LIVE"

                    for record in source.stream_records(active_well):
                        if not self._running:
                            break
                        self._process_message(json.dumps(record.to_dict()))
                        await asyncio.sleep(0.08)

                except Exception as e:
                    logger.debug(f"In-process stream loop ended or errored: {e}")

            if self._running:
                await asyncio.sleep(2.0)

    def _process_message(self, message_str: str) -> None:
        try:
            data = json.loads(message_str)
            if data.get("status") == "CONNECTED":
                return

            rec = SensorRecord.from_dict(data)
            with self._lock:
                # Detect well reset or new stream start
                if self.current_md > 0 and rec.md < self.current_md:
                    self.history.clear()

                self.well_id = rec.well_id
                self.current_md = rec.md
                self.tvd = rec.tvd
                self.last_timestamp = rec.timestamp
                self.samples_received += 1
                self.current_record = rec.to_dict()
                self.history.append(rec.to_dict())

                # Evaluate ML adapter on emitted causal history
                df_causal = pd.DataFrame(list(self.history))
                self.ml_result = self.ml_adapter.process_causal_position(
                    buffer_or_records=df_causal, cutoff_md=rec.md
                )
        except Exception as e:
            logger.error(f"Error processing stream message: {e}")

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self.status,
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
