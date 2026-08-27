import pandas as pd
import numpy as np
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class CausalFeatureConfig:
    windows: List[float] = None
    sensor_channels: List[str] = None
    
    def __post_init__(self):
        if self.windows is None:
            self.windows = [5.0, 10.0, 25.0, 50.0]
        if self.sensor_channels is None:
            self.sensor_channels = [
                'rop', 'wob', 'rpm', 'torque', 
                'hookload', 'spp', 'flow_in', 'mud_density'
            ]

def construct_causal_features(df_sensor: pd.DataFrame, cutoff_md: float, config: CausalFeatureConfig) -> Dict[str, float]:
    """
    Constructs features using strictly data <= cutoff_md.
    No future information is allowed.
    """
    df_past = df_sensor[df_sensor['md'] <= cutoff_md].copy()
    
    if len(df_past) == 0:
        raise ValueError(f"No sensor history available before cutoff {cutoff_md}")
        
    df_past = df_past.sort_values('md')
    
    latest_md = df_past['md'].iloc[-1]
    
    # CRITICAL LEAKAGE ASSERTIONS
    assert latest_md <= cutoff_md, f"Leakage detected: {latest_md} > {cutoff_md}"
    assert (df_past['md'] > cutoff_md).sum() == 0, "Post-onset data found in past window"
    
    features = {}
    
    if cutoff_md - latest_md > 5.0:
        raise ValueError(f"Sensor gap too large: nearest sample is {cutoff_md - latest_md}m away")
        
    for col in config.sensor_channels:
        if col not in df_past.columns:
            continue
            
        series = df_past[col].values
        mds = df_past['md'].values
        
        # Recent state (last value)
        features[f'{col}_current'] = float(series[-1])
        
        for w in config.windows:
            mask = (mds >= (latest_md - w)) & (mds <= latest_md)
            window_data = series[mask]
            
            if len(window_data) > 0:
                features[f'{col}_mean_{w}m'] = float(np.mean(window_data))
                features[f'{col}_std_{w}m'] = float(np.std(window_data))
                features[f'{col}_min_{w}m'] = float(np.min(window_data))
                features[f'{col}_max_{w}m'] = float(np.max(window_data))
                features[f'{col}_delta_{w}m'] = float(window_data[-1] - window_data[0])
                
                # Simple slope
                if len(window_data) > 1 and (mds[mask][-1] - mds[mask][0]) > 0:
                    features[f'{col}_slope_{w}m'] = features[f'{col}_delta_{w}m'] / (mds[mask][-1] - mds[mask][0])
                else:
                    features[f'{col}_slope_{w}m'] = 0.0
            else:
                features[f'{col}_mean_{w}m'] = np.nan
                features[f'{col}_std_{w}m'] = np.nan
                features[f'{col}_min_{w}m'] = np.nan
                features[f'{col}_max_{w}m'] = np.nan
                features[f'{col}_delta_{w}m'] = np.nan
                features[f'{col}_slope_{w}m'] = np.nan
                
        # --- Experiment A: Domain Invariant Features ---
        mean_25m = features.get(f'{col}_mean_25.0m', np.nan)
        if not pd.isna(mean_25m) and mean_25m != 0:
            mean_5m = features.get(f'{col}_mean_5.0m', np.nan)
            mean_10m = features.get(f'{col}_mean_10.0m', np.nan)
            std_25m = features.get(f'{col}_std_25.0m', np.nan)
            delta_5m = features.get(f'{col}_delta_5.0m', np.nan)
            slope_25m = features.get(f'{col}_slope_25.0m', np.nan)
            
            features[f'{col}_ratio_5m_25m'] = float(mean_5m / mean_25m) if not pd.isna(mean_5m) else np.nan
            features[f'{col}_ratio_10m_25m'] = float(mean_10m / mean_25m) if not pd.isna(mean_10m) else np.nan
            features[f'{col}_rel_delta_5m'] = float(delta_5m / mean_25m) if not pd.isna(delta_5m) else np.nan
            features[f'{col}_cv_25m'] = float(std_25m / mean_25m) if not pd.isna(std_25m) else np.nan
            features[f'{col}_norm_slope_25m'] = float(slope_25m / mean_25m) if not pd.isna(slope_25m) else np.nan
        else:
            features[f'{col}_ratio_5m_25m'] = np.nan
            features[f'{col}_ratio_10m_25m'] = np.nan
            features[f'{col}_rel_delta_5m'] = np.nan
            features[f'{col}_cv_25m'] = np.nan
            features[f'{col}_norm_slope_25m'] = np.nan
            
    return features
