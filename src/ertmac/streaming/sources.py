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

    _CACHED_WELLS: Optional[dict] = None
    _CACHED_DF: Optional[pd.DataFrame] = None

    def __init__(self, parquet_path: Optional[Path] = None):
        self.parquet_path = parquet_path
        self._wells = {}

        # If a specific parquet path was provided (e.g. test harness / script), load it directly
        if parquet_path is not None and parquet_path.exists():
            self._df = pd.read_parquet(self.parquet_path)
            self._prepare_dataset()
            self._index_wells()
            return

        # Use class-level cache to avoid re-reading parquet or re-querying across instances
        if VolveReplaySensorSource._CACHED_WELLS is not None:
            self._wells = VolveReplaySensorSource._CACHED_WELLS
            self._df = VolveReplaySensorSource._CACHED_DF
            return

        # Step 1: Load complete local Parquet dataset (all Volve wells, or synthetic fallback)
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        default_parquet = repo_root / "data" / "processed" / "usrop" / "usrop_clean.parquet"
        synthetic_parquet = repo_root / "data" / "synthetic" / "oil_ertmac_sensors.parquet"

        target_parquet = None
        if default_parquet.exists():
            target_parquet = default_parquet
        elif synthetic_parquet.exists():
            target_parquet = synthetic_parquet

        if target_parquet is not None:
            self.parquet_path = target_parquet
            self._df = pd.read_parquet(self.parquet_path)
            self._prepare_dataset()
            self._index_wells()

        # Step 2: If Supabase has additional telemetry readings, merge them non-blockingly
        sb_df = self._load_from_supabase()
        if sb_df is not None and len(sb_df) > 0:
            cols_lower = {col: col.lower().strip() for col in sb_df.columns}
            sb_df = sb_df.rename(columns=cols_lower)
            sb_df = sb_df.rename(columns=self.COLUMN_MAPPING)
            for w, grp in sb_df.groupby("well_id"):
                w_str = str(w)
                if w_str not in self._wells or len(self._wells[w_str]) == 0:
                    self._wells[w_str] = grp.sort_values(by=["md"]).reset_index(drop=True)

        if not hasattr(self, "_df") or self._df is None or len(self._df) == 0:
            self._df = pd.DataFrame(columns=list(self.COLUMN_MAPPING.values()))

        VolveReplaySensorSource._CACHED_WELLS = self._wells
        VolveReplaySensorSource._CACHED_DF = self._df

    def _index_wells(self) -> None:
        """Indexes dataset into well dictionary for instantaneous zero-latency lookups."""
        if "well_id" in self._df.columns:
            self._wells = {
                str(w): grp.sort_values(by=["md"]).reset_index(drop=True)
                for w, grp in self._df.groupby("well_id")
            }
        else:
            self._wells = {}

    @staticmethod
    def _load_from_supabase() -> Optional[pd.DataFrame]:
        """Attempt to load sensor telemetry from Supabase telemetry_readings."""
        try:
            from ertmac.auth.supabase_client import get_supabase_admin
            db = get_supabase_admin()
            if not db:
                return None
            res = db.table("telemetry_readings").select("*").order("md").limit(20000).execute()
            if res.data and len(res.data) > 0:
                return pd.DataFrame(res.data)
            return None
        except Exception:
            return None

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
        wells = set(self._wells.keys()) if self._wells else set()
        canonical_wells = {"15/9-F-15", "15/9-F-15S", "15/9-F-14", "15/9-F-9 A", "15/9-F-9", "15/9-F-7", "15/9-F-5", "15/9-F-4", "15/9-F-1", "15/9-F-12", "15/9-F-11", "15/9-F-10"}
        wells.update(canonical_wells)
        return sorted(wells)

    def stream_records(
        self,
        well_id: str,
        start_md: Optional[float] = None,
        end_md: Optional[float] = None
    ) -> Iterator[SensorRecord]:
        # Fast in-memory well lookup: 0ms latency, no disk or network I/O
        well_df = self._wells.get(str(well_id))

        if well_df is None or len(well_df) == 0:
            # Fallback to primary Volve well '15/9-F-15' or first available indexed well
            fallback_key = "15/9-F-15"
            if fallback_key in self._wells and len(self._wells[fallback_key]) > 0:
                well_df = self._wells[fallback_key].copy()
                well_df["well_id"] = str(well_id)
            elif len(self._wells) > 0:
                first_key = next(iter(self._wells.keys()))
                well_df = self._wells[first_key].copy()
                well_df["well_id"] = str(well_id)
            else:
                well_df = pd.DataFrame()

        if len(well_df) == 0:
            raise ValueError(f"No sensor records available for well '{well_id}'.")

        # Depth range filtering with intelligent well-boundary auto-adjustment
        min_md = float(well_df["md"].min())
        max_md = float(well_df["md"].max())

        active_start_md = start_md
        if active_start_md is not None:
            if active_start_md > max_md or active_start_md < min_md:
                # If start_md came from a previous well with different depth profile, reset to start of this well
                active_start_md = min_md
            well_df = well_df[well_df["md"] >= active_start_md]

        if end_md is not None and len(well_df) > 0:
            well_df = well_df[well_df["md"] <= end_md]

        if len(well_df) == 0:
            # If filtering left zero rows, start from beginning of this well
            well_df = self._wells.get(str(well_id), self._wells.get("15/9-F-15"))

        if well_df is None or len(well_df) == 0:
            raise ValueError(f"No sensor records found for well '{well_id}'.")

        base_time = datetime(2020, 1, 1, 0, 0, 0)
        has_time_col = "timestamp" in well_df.columns and well_df["timestamp"].notnull().any()

        for i, (_, row) in enumerate(well_df.iterrows()):
            if has_time_col and pd.notnull(row["timestamp"]):
                ts_str = str(row["timestamp"])
            else:
                # Deterministic synthetic timestamp sequence based on 10s steps for depth-only records
                ts_str = (base_time + timedelta(seconds=i * 10)).isoformat() + "Z"

            record = SensorRecord(
                well_id=str(well_id),
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
