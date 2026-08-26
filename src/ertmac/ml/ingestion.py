import pandas as pd
import numpy as np

class IngestionValidator:
    REQUIRED_EVENT_COLS = [
        "well_id", "wellbore_id", "timestamp", "md",
        "event_type", "event_text", "mitigation", "resolution"
    ]
    
    REQUIRED_SENSOR_COLS = [
        "well_id", "wellbore_id", "timestamp", "md", "tvd",
        "rop", "wob", "rpm", "torque", "hookload", "spp",
        "flow_in", "mud_density"
    ]
    
    def validate_event_data(self, df: pd.DataFrame) -> dict:
        missing_cols = [c for c in self.REQUIRED_EVENT_COLS if c not in df.columns]
        if missing_cols:
            raise ValueError(f"Event data missing required columns: {missing_cols}")
            
        report = {
            "total_rows": len(df),
            "unique_wells": df["well_id"].nunique(),
            "unique_wellbores": df["wellbore_id"].nunique(),
            "event_counts": df["event_type"].value_counts().to_dict(),
            "null_md_count": df["md"].isnull().sum(),
        }
        return report

    def validate_sensor_data(self, df: pd.DataFrame) -> dict:
        missing_cols = [c for c in self.REQUIRED_SENSOR_COLS if c not in df.columns]
        if missing_cols:
            raise ValueError(f"Sensor data missing required columns: {missing_cols}")
            
        # Detect duplicates
        duplicates = df.duplicated(subset=["well_id", "timestamp", "md"]).sum()
        
        # Detect non-monotonic depth sequences per well
        non_monotonic = 0
        df = df.sort_values(["well_id", "timestamp"])
        for _, group in df.groupby("well_id"):
            diffs = group["md"].diff().dropna()
            non_monotonic += (diffs < 0).sum()
            
        report = {
            "total_rows": len(df),
            "unique_wells": df["well_id"].nunique(),
            "duplicate_rows": int(duplicates),
            "non_monotonic_depth_steps": int(non_monotonic),
            "null_counts": df[self.REQUIRED_SENSOR_COLS].isnull().sum().to_dict()
        }
        return report
        
    def check_readiness(self, event_df: pd.DataFrame, sensor_df: pd.DataFrame) -> tuple[bool, str]:
        # 1. Check >=5 positive wells
        pos_wells = event_df[event_df['event_type'] == 'FORMATION_MUD_LOSS']['well_id'].unique()
        if len(pos_wells) < 5:
            return False, f"Only {len(pos_wells)} positive wells found. Minimum 5 required."
            
        # 2. Check telemetry overlap
        sensor_wells = sensor_df['well_id'].unique()
        overlapping = set(pos_wells).intersection(set(sensor_wells))
        if len(overlapping) < 5:
            return False, f"Telemetry only covers {len(overlapping)} positive wells. Minimum 5 required."
            
        # 3. Check telemetry reaching onset_md - 25m
        valid_wells = 0
        for w in overlapping:
            w_events = event_df[(event_df['well_id'] == w) & (event_df['event_type'] == 'FORMATION_MUD_LOSS')]
            w_sensor = sensor_df[sensor_df['well_id'] == w]
            min_sensor_md = w_sensor['md'].min()
            
            for _, ev in w_events.iterrows():
                cutoff = ev['md'] - 25.0
                if pd.notnull(cutoff) and min_sensor_md <= cutoff:
                    valid_wells += 1
                    break # One valid event is enough to count the well
                    
        if valid_wells < 5:
            return False, f"Telemetry does not reach onset - 25m for enough wells. Only {valid_wells} valid wells."
            
        return True, "READY_FOR_FIRST_ML_EXPERIMENT"
