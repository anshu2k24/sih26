from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from ertmac.streaming.schemas import SensorRecord, SCIENTIFIC_LABEL
from ertmac.ml.normalization import normalize_columns

class BaseSensorSource(ABC):
    """
    Abstract Base Class for sensor data sources.
    """
    @abstractmethod
    def get_available_wells(self) -> List[str]:
        """Returns list of valid well IDs supported by this source."""
        pass

    @abstractmethod
    def stream_records(
        self,
        well_id: str,
        start_md: Optional[float] = None,
        end_md: Optional[float] = None
    ) -> Iterator[SensorRecord]:
        """Yields SensorRecords in strict chronological/depth order."""
        pass


class VolveReplaySensorSource(BaseSensorSource):
    """
    Historical Replay Sensor Source for REAL Volve USROP Dataset.
    Strictly replays real source rows without fabrication, interpolation, or alteration.
    """
    COLUMN_MAPPING = {
        "well_id": "well_id",
        "measured depth m": "md",
        "hole depth (tvd) m": "tvd",
        "rate of penetration m/h": "rop",
        "weight on bit kkgf": "wob",
        "average rotary speed rpm": "rpm",
        "average surface torque kn.m": "torque",
        "average hookload kkgf": "hookload",
        "average standpipe pressure kpa": "spp",
        "mud flow in l/min": "flow_in",
        "mud density in g/cm3": "mud_density",
    }

    def __init__(self, parquet_path: Optional[Path] = None):
        if parquet_path is None:
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            parquet_path = repo_root / "data" / "processed" / "usrop" / "usrop_clean.parquet"

        if not parquet_path.exists():
            raise FileNotFoundError(
                f"Source Volve Parquet missing at: {parquet_path}. "
                f"Run audit or verification scripts to prepare dataset."
            )

        self.parquet_path = parquet_path
        self._df = pd.read_parquet(self.parquet_path)
        self._prepare_dataset()

    def _prepare_dataset(self) -> None:
        """Standardize column names to canonical schema without modifying values."""
        df = self._df.copy()

        # Lowercase column names for clean mapping
        cols_lower = {col: col.lower().strip() for col in df.columns}
        df = df.rename(columns=cols_lower)

        # Map USROP specific headers to canonical sensor names
        df = df.rename(columns=self.COLUMN_MAPPING)

        # Sort deterministically by well_id and Measured Depth (md)
        df = df.sort_values(by=["well_id", "md"]).reset_index(drop=True)
        self._df = df

    def get_available_wells(self) -> List[str]:
        return sorted(self._df["well_id"].dropna().unique().tolist())

    def stream_records(
        self,
        well_id: str,
        start_md: Optional[float] = None,
        end_md: Optional[float] = None
    ) -> Iterator[SensorRecord]:
        wells = self.get_available_wells()
        if well_id not in wells:
            raise ValueError(
                f"Invalid well_id '{well_id}'. Available Volve wells: {wells}"
            )

        well_df = self._df[self._df["well_id"] == well_id].copy()

        if start_md is not None:
            well_df = well_df[well_df["md"] >= start_md]
        if end_md is not None:
            well_df = well_df[well_df["md"] <= end_md]

        if len(well_df) == 0:
            raise ValueError(
                f"No sensor records found for well '{well_id}' in range MD [{start_md}, {end_md}]."
            )

        base_time = datetime(2020, 1, 1, 0, 0, 0)
        has_time_col = "timestamp" in well_df.columns and well_df["timestamp"].notnull().any()

        for i, (_, row) in enumerate(well_df.iterrows()):
            if has_time_col and pd.notnull(row["timestamp"]):
                ts_str = str(row["timestamp"])
            else:
                # Deterministic synthetic timestamp sequence based on 10s steps for depth-only records
                ts_str = (base_time + timedelta(seconds=i * 10)).isoformat() + "Z"

            record = SensorRecord(
                well_id=str(row["well_id"]),
                timestamp=ts_str,
                md=float(row["md"]),
                tvd=float(row["tvd"]) if "tvd" in row and pd.notnull(row["tvd"]) else None,
                rop=float(row["rop"]) if "rop" in row and pd.notnull(row["rop"]) else None,
                wob=float(row["wob"]) if "wob" in row and pd.notnull(row["wob"]) else None,
                rpm=float(row["rpm"]) if "rpm" in row and pd.notnull(row["rpm"]) else None,
                torque=float(row["torque"]) if "torque" in row and pd.notnull(row["torque"]) else None,
                hookload=float(row["hookload"]) if "hookload" in row and pd.notnull(row["hookload"]) else None,
                spp=float(row["spp"]) if "spp" in row and pd.notnull(row["spp"]) else None,
                flow_in=float(row["flow_in"]) if "flow_in" in row and pd.notnull(row["flow_in"]) else None,
                mud_density=float(row["mud_density"]) if "mud_density" in row and pd.notnull(row["mud_density"]) else None,
            )
            yield record


class SyntheticSensorSource(BaseSensorSource):
    """
    Adapter wrapper over existing `generate_synthetic_well` in `src/ertmac/ml/synthetic.py`.
    Used only when synthetic mode is explicitly requested.
    """
    def __init__(self, num_wells: int = 4):
        from ertmac.ml.synthetic import build_synthetic_dataset
        self.num_wells = num_wells
        _, self._df = build_synthetic_dataset(num_wells=num_wells)

    def get_available_wells(self) -> List[str]:
        return sorted(self._df["well_id"].unique().tolist())

    def stream_records(
        self,
        well_id: str,
        start_md: Optional[float] = None,
        end_md: Optional[float] = None
    ) -> Iterator[SensorRecord]:
        wells = self.get_available_wells()
        if well_id not in wells:
            raise ValueError(f"Invalid synthetic well_id '{well_id}'. Available: {wells}")

        df = self._df[self._df["well_id"] == well_id].sort_values("md")
        if start_md is not None:
            df = df[df["md"] >= start_md]
        if end_md is not None:
            df = df[df["md"] <= end_md]

        for _, row in df.iterrows():
            ts_str = str(row["timestamp"]) if pd.notnull(row.get("timestamp")) else datetime.utcnow().isoformat() + "Z"
            yield SensorRecord(
                well_id=str(row["well_id"]),
                timestamp=ts_str,
                md=float(row["md"]),
                tvd=float(row["tvd"]) if "tvd" in row and pd.notnull(row["tvd"]) else None,
                rop=float(row["rop"]) if "rop" in row and pd.notnull(row["rop"]) else None,
                wob=float(row["wob"]) if "wob" in row and pd.notnull(row["wob"]) else None,
                rpm=float(row["rpm"]) if "rpm" in row and pd.notnull(row["rpm"]) else None,
                torque=float(row["torque"]) if "torque" in row and pd.notnull(row["torque"]) else None,
                hookload=float(row["hookload"]) if "hookload" in row and pd.notnull(row["hookload"]) else None,
                spp=float(row["spp"]) if "spp" in row and pd.notnull(row["spp"]) else None,
                flow_in=float(row["flow_in"]) if "flow_in" in row and pd.notnull(row["flow_in"]) else None,
                mud_density=float(row["mud_density"]) if "mud_density" in row and pd.notnull(row["mud_density"]) else None,
            )


class ERTMACSensorSource(BaseSensorSource):
    """
    Interface/Stub for future real-time physical eRTMAC sensor hardware acquisition.
    """
    def __init__(self, endpoint_uri: str = "witsml://localhost:7111"):
        self.endpoint_uri = endpoint_uri

    def get_available_wells(self) -> List[str]:
        return ["ERTMAC-LIVE-01"]

    def stream_records(
        self,
        well_id: str,
        start_md: Optional[float] = None,
        end_md: Optional[float] = None
    ) -> Iterator[SensorRecord]:
        raise NotImplementedError(
            f"Physical eRTMAC live sensor stream ({self.endpoint_uri}) requires hardware deployment."
        )
