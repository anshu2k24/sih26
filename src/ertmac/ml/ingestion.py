import pandas as pd
from typing import Dict, List, Tuple
from .normalization import CANONICAL_EVENTS, CANONICAL_SENSORS

class IngestionValidator:
    def __init__(self, explicit_mappings: Dict[str, str] = None):
        """
        Never automatically merge parent wells and sidetracks unless explicitly supplied.
        explicit_mappings: Dict mapping 'wellbore_id' to 'independent_well_group'
        Example: {'15/9-F-15S': '15/9-F-15'}
        """
        self.explicit_mappings = explicit_mappings or {}
        
    def get_independent_group(self, well_id: str, wellbore_id: str) -> Tuple[str, str, str]:
        """
        Returns (independent_well_group, mapping_confidence, mapping_reason)
        """
        # If explicitly provided
        if wellbore_id in self.explicit_mappings:
            return self.explicit_mappings[wellbore_id], "HIGH", "Explicitly supplied relationship"
        if well_id in self.explicit_mappings:
            return self.explicit_mappings[well_id], "HIGH", "Explicitly supplied relationship"
            
        # Do not automatically strip suffixes. Treat each well_id as its own independent group.
        return well_id, "HIGH", "Canonical well_id used directly"

    def assign_mappings(self, df: pd.DataFrame) -> pd.DataFrame:
        groups = []
        confidences = []
        reasons = []
        
        for _, row in df.iterrows():
            w_id = str(row.get('well_id', ''))
            wb_id = str(row.get('wellbore_id', ''))
            g, c, r = self.get_independent_group(w_id, wb_id)
            groups.append(g)
            confidences.append(c)
            reasons.append(r)
            
        df['independent_well_group'] = groups
        df['mapping_confidence'] = confidences
        df['mapping_reason'] = reasons
        return df

    def validate_event_data(self, df: pd.DataFrame) -> dict:
        df = self.assign_mappings(df)
        report = {
            "total_rows": len(df),
            "unique_wells": df["well_id"].nunique(),
            "unique_wellbores": df["wellbore_id"].nunique(),
            "independent_groups": df["independent_well_group"].nunique(),
            "event_counts": df["event_type"].value_counts().to_dict(),
            "null_md_count": df["md"].isnull().sum(),
        }
        return report

    def validate_sensor_data(self, df: pd.DataFrame) -> dict:
        df = self.assign_mappings(df)
        duplicates = df.duplicated(subset=["well_id", "timestamp", "md"]).sum()
        
        non_monotonic = 0
        df_sorted = df.sort_values(["well_id", "timestamp"])
        for _, group in df_sorted.groupby("well_id"):
            diffs = group["md"].diff().dropna()
            non_monotonic += (diffs < 0).sum()
            
        gaps_5m = 0
        for _, group in df_sorted.groupby("well_id"):
            diffs = group["md"].diff().dropna()
            gaps_5m += (diffs > 5.0).sum()
            
        report = {
            "total_rows": len(df),
            "unique_wells": df["well_id"].nunique(),
            "unique_wellbores": df["wellbore_id"].nunique(),
            "duplicate_rows": int(duplicates),
            "non_monotonic_depth_steps": int(non_monotonic),
            "telemetry_gaps_gt_5m": int(gaps_5m),
            "null_counts": df[CANONICAL_SENSORS].isnull().sum().to_dict()
        }
        return report
        
    def check_readiness(self, event_df: pd.DataFrame, sensor_df: pd.DataFrame) -> tuple[bool, str, dict]:
        if len(sensor_df) == 0:
            return False, "Minimum 5 required. Zero telemetry provided.", {}
            
        event_df = self.assign_mappings(event_df)
        sensor_df = self.assign_mappings(sensor_df)
        
        # Filter for Target
        target_events = event_df[event_df['event_type'] == 'FORMATION_MUD_LOSS'].copy()
        
        pos_groups = target_events['independent_well_group'].unique()
        if len(pos_groups) < 5:
            return False, f"Only {len(pos_groups)} independent positive well groups found. Minimum 5 required.", {"pos_groups": len(pos_groups)}
            
        sensor_groups = sensor_df['independent_well_group'].unique()
        overlapping = set(pos_groups).intersection(set(sensor_groups))
        if len(overlapping) < 5:
            return False, f"Telemetry only covers {len(overlapping)} independent positive well groups. Minimum 5 required.", {"overlapping": len(overlapping)}
            
        valid_groups_25m = set()
        valid_groups_50m = set()
        valid_groups_100m = set()
        
        for g in overlapping:
            g_events = target_events[target_events['independent_well_group'] == g]
            g_sensor = sensor_df[sensor_df['independent_well_group'] == g]
            
            if len(g_sensor) == 0: continue
            min_sensor_md = g_sensor['md'].min()
            
            for _, ev in g_events.iterrows():
                if pd.isnull(ev['md']): continue
                if min_sensor_md <= (ev['md'] - 25.0): valid_groups_25m.add(g)
                if min_sensor_md <= (ev['md'] - 50.0): valid_groups_50m.add(g)
                if min_sensor_md <= (ev['md'] - 100.0): valid_groups_100m.add(g)
                    
        stats = {
            "total_wells": event_df["well_id"].nunique(),
            "total_wellbores": event_df["wellbore_id"].nunique(),
            "independent_groups": event_df["independent_well_group"].nunique(),
            "verified_positive_groups": len(pos_groups),
            "sensor_overlap_groups": len(overlapping),
            "coverage_25m_horizon": len(valid_groups_25m),
            "coverage_50m_horizon": len(valid_groups_50m),
            "coverage_100m_horizon": len(valid_groups_100m),
        }
                    
        if len(valid_groups_25m) < 5:
            return False, f"Telemetry does not reach onset - 25m for enough independent groups. Only {len(valid_groups_25m)} valid groups.", stats
            
        return True, "READY_FOR_FIRST_ML_EXPERIMENT", stats
