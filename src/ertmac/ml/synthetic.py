import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, List, Dict
import random

def generate_synthetic_well(
    well_id: str, 
    start_md: float, 
    end_md: float, 
    start_time: datetime,
    has_event: bool = False,
    event_type: str = 'FORMATION_MUD_LOSS',
    random_seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    np.random.seed(random_seed)
    random.seed(random_seed)
    
    md_step = 1.0
    num_samples = int((end_md - start_md) / md_step)
    md_arr = np.linspace(start_md, end_md, num_samples)
    tvd_arr = md_arr * 0.95 + np.cumsum(np.random.normal(0, 0.01, num_samples))
    
    # 3 mins/m + noise
    time_steps = [start_time + timedelta(minutes=int(3*i + np.random.normal(0, 0.5))) for i in range(num_samples)]
    
    # Generate continuous baseline latent variables
    rock_strength = np.cumsum(np.random.normal(0, 0.1, num_samples))
    rock_strength = np.clip(rock_strength, -2, 2)
    
    # Base physics
    flow_in_base = 800.0 + np.random.normal(0, 5, num_samples)
    spp_base = 3.0 * flow_in_base + 100.0 * rock_strength + np.random.normal(0, 20, num_samples)
    
    wob_base = 15.0 + 5.0 * rock_strength + np.random.normal(0, 2, num_samples)
    torque_base = 1.5 * wob_base + 5.0 * rock_strength + np.random.normal(0, 1, num_samples)
    
    rpm_base = 120.0 + np.random.normal(0, 2, num_samples)
    rop_base = 0.5 * rpm_base + 0.2 * wob_base - 5.0 * rock_strength + np.random.normal(0, 3, num_samples)
    
    hookload_base = 150.0 + (md_arr / 1000) * 10 - wob_base + np.random.normal(0, 5, num_samples)
    mud_density_base = 1.20 + np.cumsum(np.random.normal(0, 0.001, num_samples))
    
    # Operational Regimes (10% chance of connection -> rop=0, wob=0, rpm=0, torque=0, spp drops)
    regimes = np.random.choice(['drilling', 'connection'], p=[0.9, 0.1], size=num_samples)
    
    for i in range(num_samples):
        if regimes[i] == 'connection':
            rop_base[i] = 0.0
            wob_base[i] = 0.0
            rpm_base[i] = 0.0
            torque_base[i] = 0.0
            spp_base[i] *= 0.1 # pumps off
            flow_in_base[i] *= 0.1
            
    # Hard Negatives (False precursors: sudden drops in SPP or surges in ROP not causing an event)
    num_hard_negatives = np.random.randint(1, 4)
    for _ in range(num_hard_negatives):
        hn_idx = np.random.randint(100, num_samples - 100)
        # SPP sudden drop + Flow in spike
        length = np.random.randint(10, 30)
        spp_base[hn_idx:hn_idx+length] -= np.random.uniform(100, 400, length)
        # Add some noise to the drop
        spp_base[hn_idx:hn_idx+length] += np.random.normal(0, 50, length)
    
    events_list = []
    
    if has_event:
        event_idx = int(num_samples * np.random.uniform(0.6, 0.9))
        event_md = md_arr[event_idx]
        event_time = time_steps[event_idx]
        
        precursor_len = np.random.randint(20, 100)
        precursor_start = max(0, event_idx - precursor_len)
        
        precursor_type = np.random.choice(['strong', 'weak', 'delayed'])
        
        if precursor_type == 'strong':
            # Noisy gradual drop
            drop = np.linspace(0, 1, event_idx - precursor_start) + np.random.normal(0, 0.1, event_idx - precursor_start)
            drop = np.clip(drop, 0, 1.5)
            spp_base[precursor_start:event_idx] -= 300.0 * drop
            rop_base[precursor_start:event_idx] += 20.0 * drop
        elif precursor_type == 'weak':
            # Less pronounced, noisier
            drop = np.linspace(0, 0.5, event_idx - precursor_start) + np.random.normal(0, 0.2, event_idx - precursor_start)
            spp_base[precursor_start:event_idx] -= 100.0 * drop
        else:
            # Delayed/None: barely any precursor until last 5 meters
            short_start = max(0, event_idx - 5)
            drop = np.linspace(0, 1, event_idx - short_start) + np.random.normal(0, 0.3, event_idx - short_start)
            spp_base[short_start:event_idx] -= 200.0 * drop
            
        events_list.append({
            'well_id': well_id,
            'wellbore_id': well_id,
            'independent_well_group': well_id,
            'timestamp': event_time,
            'md': event_md,
            'event_type': event_type,
            'primary_evidence': f"[SYNTHETIC DEVELOPMENT EVENT] Simulated {event_type} signature detected. Type: {precursor_type}",
            'mitigation': "[SYNTHETIC] Pumped LCM pill.",
            'resolution': "[SYNTHETIC] Losses cured."
        })
        
    df_sensor = pd.DataFrame({
        'well_id': well_id,
        'wellbore_id': well_id,
        'independent_well_group': well_id,
        'timestamp': time_steps,
        'md': md_arr,
        'tvd': tvd_arr,
        'rop': np.clip(rop_base, 0.0, 100.0),
        'wob': np.clip(wob_base, 0.0, 40.0),
        'rpm': np.clip(rpm_base, 0.0, 200.0),
        'torque': np.clip(torque_base, 0.0, 50.0),
        'hookload': np.clip(hookload_base, 10.0, 500.0),
        'spp': np.clip(spp_base, 0.0, 5000.0),
        'flow_in': np.clip(flow_in_base, 0.0, 1500.0),
        'mud_density': np.clip(mud_density_base, 0.8, 3.0)
    })
    
    df_event = pd.DataFrame(events_list)
    return df_event, df_sensor

def build_synthetic_dataset(num_wells: int = 8, seed: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame]:
    events_all = []
    sensors_all = []
    np.random.seed(seed)
    
    start_time_base = datetime(2023, 1, 1, 0, 0, 0)
    
    for i in range(1, num_wells + 1):
        wid = f"SYN-F0{i}" if i < 10 else f"SYN-F{i}"
        start_md = np.random.uniform(500.0, 1000.0)
        end_md = start_md + np.random.uniform(2000.0, 3000.0)
        
        has_event = i <= 6
        df_e, df_s = generate_synthetic_well(
            well_id=wid, start_md=start_md, end_md=end_md,
            start_time=start_time_base + timedelta(days=i*10),
            has_event=has_event, event_type='FORMATION_MUD_LOSS', random_seed=seed + i
        )
        events_all.append(df_e)
        sensors_all.append(df_s)
        
    df_events = pd.concat(events_all, ignore_index=True) if events_all else pd.DataFrame()
    df_sensors = pd.concat(sensors_all, ignore_index=True)
    return df_events, df_sensors
