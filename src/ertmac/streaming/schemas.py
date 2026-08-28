from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from collections import deque
import pandas as pd
import numpy as np

# Re-export CANONICAL_SENSORS from normalization contract to guarantee single source of truth
from ertmac.ml.normalization import CANONICAL_SENSORS

SCIENTIFIC_LABEL = "REAL VOLVE DATA — HISTORICAL REPLAY"

@dataclass
class SensorRecord:
    """
    Canonical sensor telemetry contract for eRTMAC streaming layer.
    Reuses existing ML sensor contracts and schema definitions.
    """
    well_id: str
    timestamp: str
    md: float
    tvd: Optional[float] = None
    rop: Optional[float] = None
    wob: Optional[float] = None
    rpm: Optional[float] = None
    torque: Optional[float] = None
    hookload: Optional[float] = None
    spp: Optional[float] = None
    flow_in: Optional[float] = None
    mud_density: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to strict JSON-compatible dictionary payload."""
        return {
            "well_id": str(self.well_id),
            "timestamp": str(self.timestamp),
            "md": None if pd.isnull(self.md) else float(self.md),
            "tvd": None if (self.tvd is None or pd.isnull(self.tvd)) else float(self.tvd),
            "rop": None if (self.rop is None or pd.isnull(self.rop)) else float(self.rop),
            "wob": None if (self.wob is None or pd.isnull(self.wob)) else float(self.wob),
            "rpm": None if (self.rpm is None or pd.isnull(self.rpm)) else float(self.rpm),
            "torque": None if (self.torque is None or pd.isnull(self.torque)) else float(self.torque),
            "hookload": None if (self.hookload is None or pd.isnull(self.hookload)) else float(self.hookload),
            "spp": None if (self.spp is None or pd.isnull(self.spp)) else float(self.spp),
            "flow_in": None if (self.flow_in is None or pd.isnull(self.flow_in)) else float(self.flow_in),
            "mud_density": None if (self.mud_density is None or pd.isnull(self.mud_density)) else float(self.mud_density),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SensorRecord":
        return cls(
            well_id=str(d.get("well_id", "")),
            timestamp=str(d.get("timestamp", "")),
            md=float(d.get("md", 0.0)),
            tvd=None if pd.isnull(d.get("tvd")) else float(d["tvd"]),
            rop=None if pd.isnull(d.get("rop")) else float(d["rop"]),
            wob=None if pd.isnull(d.get("wob")) else float(d["wob"]),
            rpm=None if pd.isnull(d.get("rpm")) else float(d["rpm"]),
            torque=None if pd.isnull(d.get("torque")) else float(d["torque"]),
            hookload=None if pd.isnull(d.get("hookload")) else float(d["hookload"]),
            spp=None if pd.isnull(d.get("spp")) else float(d["spp"]),
            flow_in=None if pd.isnull(d.get("flow_in")) else float(d["flow_in"]),
            mud_density=None if pd.isnull(d.get("mud_density")) else float(d["mud_density"]),
        )


@dataclass
class StreamState:
    """
    Maintains latest state for a single active well stream.
    """
    well_id: str
    current_md: float = 0.0
    last_timestamp: str = ""
    emitted_count: int = 0
    latest_record: Optional[SensorRecord] = None
    data_label: str = SCIENTIFIC_LABEL


class CausalStreamBuffer:
    """
    Bounded rolling history buffer enforcing causal leakage protection.
    Retains enough history for 5m, 10m, 25m, 50m, 100m depth windows while capping
    maximum memory usage.
    """
    def __init__(self, max_records: int = 10000, max_depth_span_m: float = 200.0):
        self.max_records = max_records
        self.max_depth_span_m = max_depth_span_m
        self._buffer: deque = deque(maxlen=max_records)
        self.state = StreamState(well_id="")

    def append(self, record: SensorRecord) -> None:
        """
        Append record to buffer after verifying causal depth order.
        """
        if self.state.latest_record is not None:
            # Enforce non-regressive stream position
            if record.md < self.state.current_md:
                raise ValueError(
                    f"Leakage Protection Violation: Out-of-order record received. "
                    f"Record MD {record.md} < current position {self.state.current_md}"
                )

        self._buffer.append(record)
        self.state.well_id = record.well_id
        self.state.current_md = record.md
        self.state.last_timestamp = record.timestamp
        self.state.emitted_count += 1
        self.state.latest_record = record

        # Prune records older than max depth span to maintain bounded memory
        cutoff_md = record.md - self.max_depth_span_m
        while self._buffer and self._buffer[0].md < cutoff_md:
            self._buffer.popleft()

    def get_history_at_cutoff(self, cutoff_md: float) -> List[SensorRecord]:
        """
        LEAKAGE PROTECTION GATEWAY:
        Returns strictly causal history where MD <= cutoff_md.
        Future records (> cutoff_md) are invisible to downstream consumers.
        """
        return [r for r in self._buffer if r.md <= cutoff_md]

    def get_depth_window(self, window_m: float) -> List[SensorRecord]:
        """
        Extracts historical sensor records within [current_md - window_m, current_md].
        Supports existing causal feature requirements for 5m, 10m, 25m, 50m, 100m.
        """
        current_md = self.state.current_md
        start_md = current_md - window_m
        return [r for r in self._buffer if start_md <= r.md <= current_md]

    def to_dataframe(self, cutoff_md: Optional[float] = None) -> pd.DataFrame:
        """
        Converts causal buffer to pandas DataFrame for feature builders.
        """
        records = self._buffer if cutoff_md is None else self.get_history_at_cutoff(cutoff_md)
        if not records:
            return pd.DataFrame(columns=CANONICAL_SENSORS)
        dicts = [r.to_dict() for r in records]
        return pd.DataFrame(dicts)

    def clear(self) -> None:
        self._buffer.clear()
        self.state = StreamState(well_id="")

    def __len__(self) -> int:
        return len(self._buffer)
