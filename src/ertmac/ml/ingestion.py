import pandas as pd
import re

class IngestionValidator:
    REQUIRED_EVENT_COLS = [
        "well_id", "timestamp", "md",
        "event_type", "primary_evidence", "mitigation"
    ]
    
    REQUIRED_SENSOR_COLS = [
        "well_id", "timestamp", "md",
        "rop", "wob", "rpm", "torque", "hookload", "spp",
        "flow_in", "mud_density"
    ]
    
    def get_independent_group(self, well_id: str) -> str:
        """
        Groups parent and sidetrack wells together.
        Example: '15/9-F-15' and '15/9-F-15S' -> '15/9-F-15'
        Example: 'Well A' and 'Well A ST1' -> 'Well A'
        """
        # Very basic regex to strip common sidetrack suffixes
        return re.sub(r'(\s*[A-Z]$|\s*ST\d*$|S$|T\d*$)', '', well_id).strip()

    def validate_event_data(self, df: pd.DataFrame) -> dict:
        missing_cols = [c for c in self.REQUIRED_EVENT_COLS if c not in df.columns]
        if missing_cols:
            raise ValueError(f"Event data missing required columns: {missing_cols}")
            
        report = {
            "total_rows": len(df),
            "unique_wells": df["well_id"].nunique(),
            "independent_groups": df["well_id"].apply(self.get_independent_group).nunique(),
            "event_counts": df["event_type"].value_counts().to_dict(),
            "null_md_count": df["md"].isnull().sum(),
        }
        return report

    def validate_sensor_data(self, df: pd.DataFrame) -> dict:
        missing_cols = [c for c in self.REQUIRED_SENSOR_COLS if c not in df.columns]
        if missing_cols:
            raise ValueError(f"Sensor data missing required columns: {missing_cols}")
            
        duplicates = df.duplicated(subset=["well_id", "timestamp", "md"]).sum()
        
        non_monotonic = 0
        df_sorted = df.sort_values(["well_id", "timestamp"])
        for _, group in df_sorted.groupby("well_id"):
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
        # Filter for Target
        target_events = event_df[event_df['event_type'] == 'FORMATION_MUD_LOSS'].copy()
        
        if len(sensor_df) == 0:
            return False, "Minimum 5 required. Zero telemetry provided."
            
        target_events['independent_group'] = target_events['well_id'].apply(self.get_independent_group)
        sensor_df['independent_group'] = sensor_df['well_id'].apply(self.get_independent_group)
        
        pos_groups = target_events['independent_group'].unique()
        if len(pos_groups) < 5:
            return False, f"Only {len(pos_groups)} independent positive well groups found. Minimum 5 required."
            
        sensor_groups = sensor_df['independent_group'].unique()
        overlapping = set(pos_groups).intersection(set(sensor_groups))
        if len(overlapping) < 5:
            return False, f"Telemetry only covers {len(overlapping)} independent positive well groups. Minimum 5 required."
            
        valid_groups = set()
        for g in overlapping:
            g_events = target_events[target_events['independent_group'] == g]
            g_sensor = sensor_df[sensor_df['independent_group'] == g]
            
            if len(g_sensor) == 0: continue
            min_sensor_md = g_sensor['md'].min()
            
            for _, ev in g_events.iterrows():
                cutoff = ev['md'] - 25.0
                if pd.notnull(cutoff) and min_sensor_md <= cutoff:
                    valid_groups.add(g)
                    break
                    
        if len(valid_groups) < 5:
            return False, f"Telemetry does not reach onset - 25m for enough independent groups. Only {len(valid_groups)} valid groups."
            
        return True, "READY_FOR_FIRST_ML_EXPERIMENT"
