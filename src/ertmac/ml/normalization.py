import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path
import xml.etree.ElementTree as ET

# Canonical schema columns
CANONICAL_EVENTS = [
    "well_id", "wellbore_id", "timestamp", "md", 
    "event_type", "primary_evidence", "mitigation", "resolution"
]

CANONICAL_SENSORS = [
    "well_id", "timestamp", "md", "tvd", "rop", "wob", 
    "rpm", "torque", "hookload", "spp", "flow_in", "mud_density"
]

# Field aliases for normalization
FIELD_ALIASES = {
    "well": "well_id",
    "wellname": "well_id",
    "well_name": "well_id",
    "well name": "well_id",
    "wellbore": "wellbore_id",
    "wellborename": "wellbore_id",
    "wellbore_name": "wellbore_id",
    "date_time": "timestamp",
    "datetime": "timestamp",
    "time": "timestamp",
    "measured_depth": "md",
    "depth": "md",
    "true_vertical_depth": "tvd",
    "rate_of_penetration": "rop",
    "rop_avg": "rop",
    "weight_on_bit": "wob",
    "wob_avg": "wob",
    "rotary_speed": "rpm",
    "rpm_avg": "rpm",
    "surface_torque": "torque",
    "torq": "torque",
    "hook_load": "hookload",
    "hkld": "hookload",
    "standpipe_pressure": "spp",
    "pump_pressure": "spp",
    "mud_flow_in": "flow_in",
    "flow": "flow_in",
    "mud_weight": "mud_density",
    "mw": "mud_density",
    "event": "event_type",
    "type": "event_type",
    "evidence": "primary_evidence",
    "description": "primary_evidence",
    "action": "mitigation"
}

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).lower().strip() for c in df.columns]
    df = df.rename(columns=FIELD_ALIASES)
    return df

def handle_sentinels_and_impossible(df: pd.DataFrame, is_sensor: bool = True) -> Tuple[pd.DataFrame, Dict[str, int]]:
    invalid_counts = {}
    
    # Replace sentinels with NaN only on scalar columns
    for col in df.columns:
        if df[col].dtype.name != 'object':
            mask = df[col].isin([-999.25, -999.99])
            invalid_counts[f"{col}_sentinels"] = mask.sum()
            df[col] = df[col].replace([-999.25, -999.99], np.nan)
        else:
            try:
                # Attempt string replace for object cols that might be strings
                mask = df[col].isin(["-999.25", "-999.99", "NaN", "NA"])
                invalid_counts[f"{col}_sentinels"] = mask.sum()
                df[col] = df[col].replace(["-999.25", "-999.99", "NaN", "NA"], np.nan)
            except Exception:
                pass
    
    if "md" in df.columns:
        df["md"] = pd.to_numeric(df["md"], errors='coerce')
        # Impossible MDs (negative or unreasonably deep for this project scope)
        mask = (df["md"] < 0) | (df["md"] > 15000)
        invalid_counts["md_impossible"] = mask.sum()
        df.loc[mask, "md"] = np.nan
        
    if "tvd" in df.columns:
        df["tvd"] = pd.to_numeric(df["tvd"], errors='coerce')
        mask = (df["tvd"] < 0) | (df["tvd"] > 15000)
        invalid_counts["tvd_impossible"] = mask.sum()
        df.loc[mask, "tvd"] = np.nan
        
    if is_sensor:
        numeric_cols = [c for c in CANONICAL_SENSORS if c not in ["well_id", "timestamp"]]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # Never silently clamp. Flag and convert to NaN.
                if col in ["rop", "wob", "rpm", "spp", "flow_in", "mud_density"]:
                    mask = (df[col] < 0)
                    invalid_counts[f"{col}_negative"] = mask.sum()
                    df.loc[mask, col] = np.nan
    
    return df, {k: int(v) for k, v in invalid_counts.items() if v > 0}

def ensure_canonical(df: pd.DataFrame, schema: List[str]) -> pd.DataFrame:
    for col in schema:
        if col not in df.columns:
            df[col] = np.nan
    return df[schema].copy()

def parse_witsml(file_path: Path) -> pd.DataFrame:
    """
    Parses a basic WITSML 1.4 log file.
    Assumes standard <logCurveInfo> and <logData> structures.
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        # Find namespace
        ns = ""
        if "}" in root.tag:
            ns = root.tag.split("}")[0] + "}"
            
        log = root.find(f".//{ns}log")
        if log is None:
            return pd.DataFrame()
            
        well_id = log.findtext(f"{ns}nameWell")
        wellbore_id = log.findtext(f"{ns}nameWellbore")
        
        curves = []
        for lci in log.findall(f".//{ns}logCurveInfo"):
            curves.append(lci.findtext(f"{ns}mnemonic").lower())
            
        data = []
        for row in log.findall(f".//{ns}logData/{ns}data"):
            vals = row.text.split(",")
            data.append(vals)
            
        df = pd.DataFrame(data, columns=curves)
        df["well_id"] = well_id
        df["wellbore_id"] = wellbore_id
        return df
    except Exception as e:
        print(f"Error parsing WITSML {file_path}: {e}")
        return pd.DataFrame()

def ingest_file(file_path: Path, is_event: bool = False) -> Tuple[pd.DataFrame, Dict]:
    ext = file_path.suffix.lower()
    if ext == ".parquet":
        df = pd.read_parquet(file_path)
    elif ext == ".csv":
        df = pd.read_csv(file_path, low_memory=False)
    elif ext == ".xml":
        df = parse_witsml(file_path)
    else:
        # eRTMAC tabular exports (could be xlsx)
        try:
            df = pd.read_excel(file_path)
        except Exception:
            raise ValueError(f"Unsupported format: {ext}")
            
    df = normalize_columns(df)
    
    # Missing columns
    if "well_id" not in df.columns and "wellbore_id" in df.columns:
        df["well_id"] = df["wellbore_id"]
    if "wellbore_id" not in df.columns and "well_id" in df.columns:
        df["wellbore_id"] = df["well_id"]
        
    df, invalid_report = handle_sentinels_and_impossible(df, is_sensor=not is_event)
    
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        
    schema = CANONICAL_EVENTS if is_event else CANONICAL_SENSORS
    df = ensure_canonical(df, schema)
    
    # Deduplicate
    df = df.drop_duplicates()
    
    # Clean up MD monotonicity per wellbore
    if not is_event:
        df = df.dropna(subset=["well_id", "timestamp", "md"])
        df = df.sort_values(["well_id", "timestamp"])
        
    return df, invalid_report
