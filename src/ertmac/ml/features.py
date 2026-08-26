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
    
    features = {}
    latest_md = df_past['md'].iloc[-1]
    
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
                
    return features
