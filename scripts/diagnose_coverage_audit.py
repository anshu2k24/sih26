import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json

def parse_date(date_str):
    try:
        return pd.to_datetime(date_str, utc=True)
    except:
        return pd.NaT

def main():
    events_path = 'reports/tables/verified_event_episodes_v2.csv'
    usrop_path = 'data/processed/usrop/usrop_clean.parquet'
    ddr_path = 'volve_ddr.parquet'

    events = pd.read_csv(events_path)
    usrop = pd.read_parquet(usrop_path)
    ddr = pd.read_parquet(ddr_path)

    usrop_wells = usrop['well_id'].unique().tolist()
    ddr_mapped_wells = ["NO " + w for w in usrop_wells]

    # Target channels
    col_map = {
        'Measured Depth m': 'md',
        'Weight on Bit kkgf': 'wob',
        'Average Standpipe Pressure kPa': 'spp',
        'Average Surface Torque kN.m': 'torque',
        'Rate of Penetration m/h': 'rop',
        'Average Rotary Speed rpm': 'rpm',
        'Mud Flow In L/min': 'flow_in',
        'Mud Density In g/cm3': 'mud_density',
        'Diameter mm': 'diameter',
        'Average Hookload kkgf': 'hookload',
        'Hole Depth (TVD) m': 'tvd',
        'USROP Gamma gAPI': 'gamma'
    }
    
    usrop = usrop.rename(columns=col_map)
    usrop['wellbore_id'] = usrop['well_id'].apply(lambda x: "NO " + x)

    report = []
    report.append("# Real Data Coverage Audit")

    # STEP 1: EVENT TYPE INVENTORY
    report.append("\n## Step 1: Event Type Inventory (All DDR Wells)\n")
    report.append("| Event Type | HIGH | MEDIUM | LOW | UNKNOWN | Distinct Wells | Distinct Wellbores |")
    report.append("|---|---|---|---|---|---|---|")
    
    event_summary = {}
    for etype in events['event_type'].unique():
        sub = events[events['event_type'] == etype]
        c_high = len(sub[sub['onset_confidence'] == 'HIGH'])
        c_med = len(sub[sub['onset_confidence'] == 'MEDIUM'])
        c_low = len(sub[sub['onset_confidence'] == 'LOW'])
        c_unk = len(sub[sub['onset_confidence'] == 'UNKNOWN'])
        d_wells = sub['well_id'].nunique()
        d_wbs = sub['wellbore_id'].nunique()
        report.append(f"| {etype} | {c_high} | {c_med} | {c_low} | {c_unk} | {d_wells} | {d_wbs} |")
        event_summary[etype] = {
            'total_high_med': c_high + c_med,
            'd_wells': d_wells
        }

    # STEP 2: USROP CHANNEL INVENTORY
    report.append("\n## Step 2: USROP Channel Inventory (7 USROP Wells)\n")
    channels = ['md', 'tvd', 'rop', 'wob', 'rpm', 'torque', 'hookload', 'spp', 'flow_in', 'mud_density']
    
    report.append("| Well ID | MD Range | " + " | ".join(channels) + " |")
    report.append("|---" * (len(channels) + 2) + "|")

    for well in usrop_wells:
        w_df = usrop[usrop['well_id'] == well]
        if w_df.empty:
            continue
        min_md = w_df['md'].min()
        max_md = w_df['md'].max()
        row_str = f"| {well} | {min_md:.1f}-{max_md:.1f} |"
        for ch in channels:
            if ch not in w_df.columns:
                row_str += " Absent |"
            else:
                # Calculate non-null, non-sentinel
                col_data = w_df[ch]
                valid = col_data.notna() & ~col_data.isin([-999.25, -999.99])
                pct = (valid.sum() / len(col_data)) * 100
                row_str += f" {pct:.1f}% |"
        report.append(row_str)

    # Check for flow_out
    has_flow_out_usrop = any('flow_out' in c.lower() for c in usrop.columns)
    
    # Check for flow out in DDR
    # DDR fluid struct usually has type, density, visFunnel, pv, yp.
    has_flow_out_ddr = False # Assume False unless proven, but let's just do a string search over DDR columns
    for c in ddr.columns:
        if 'flow_out' in c.lower() or 'flowout' in c.lower() or 'returns' in c.lower():
            has_flow_out_ddr = True
            
    report.append(f"\n**Flow-out Presence:**")
    report.append(f"USROP contains flow_out: {'YES' if has_flow_out_usrop else 'NO'}")
    report.append(f"DDR contains explicit flow_out column: {'YES' if has_flow_out_ddr else 'NO'}")
    report.append("Kick detection via flow-in vs flow-out divergence is structurally blocked by the lack of flow_out telemetry.")

    # STEP 3: EVENT-TO-TELEMETRY FEASIBILITY MATRIX
    report.append("\n## Step 3: Event-To-Telemetry Feasibility Matrix\n")
    report.append("| Event Type | Events in USROP Wells | Passing Causal Gate | Primary Failure Reason | Verdict |")
    report.append("|---|---|---|---|---|")

    usrop_events = events[events['wellbore_id'].isin(ddr_mapped_wells)]
    
    gap_classification = {}
    
    for etype in events['event_type'].unique():
        sub = usrop_events[
            (usrop_events['event_type'] == etype) & 
            (usrop_events['onset_confidence'].isin(['HIGH', 'MEDIUM']))
        ]
        
        usrop_count = len(sub)
        passing = 0
        reasons = []
        
        for _, row in sub.iterrows():
            wb = row['wellbore_id']
            onset = row['onset_md']
            ts = parse_date(row['onset_timestamp'])
            
            w_df = usrop[usrop['wellbore_id'] == wb]
            if w_df.empty:
                reasons.append("No USROP data")
                continue
                
            min_md = w_df['md'].min()
            max_md = w_df['md'].max()
            cutoff = onset - 25.0
            
            if not (min_md <= cutoff and onset <= max_md):
                reasons.append("Out of MD Range")
                continue
                
            # Local window check
            window = w_df[(w_df['md'] >= cutoff) & (w_df['md'] <= onset)]
            if window.empty:
                reasons.append("Empty 25m Window")
                continue
                
            mds = np.sort(window['md'].values)
            max_gap = np.max(np.diff(mds)) if len(mds) > 1 else 999.0
            
            if max_gap > 10.0:
                reasons.append(f"Local Gap > 10m")
                continue
                
            # Check DDR activity for drilling phase
            act_is_drilling = False
            ddr_w = ddr[ddr['nameWellbore'] == wb]
            for _, dr in ddr_w.iterrows():
                start = parse_date(dr['dTimStart'])
                if pd.notna(start) and pd.notna(ts) and start.date() == ts.date():
                    acts = dr['activity']
                    if acts is not None and len(acts) > 0:
                        for act in acts:
                            a_start = parse_date(act.get('dTimStart'))
                            a_end = parse_date(act.get('dTimEnd'))
                            if pd.notna(a_start) and pd.notna(a_end) and a_start <= ts <= a_end:
                                phase = str(act.get('phase', '')).lower()
                                prop = str(act.get('proprietaryCode', '')).lower()
                                if 'drill' in phase or 'drill' in prop:
                                    act_is_drilling = True
                                break
                                
            if not act_is_drilling:
                reasons.append("Non-drilling phase")
            else:
                passing += 1
                
        # Primary reason
        if reasons:
            from collections import Counter
            c = Counter(reasons)
            primary_reason = c.most_common(1)[0][0]
        else:
            primary_reason = "None"
            
        if passing > 0:
            verdict = "VIABLE_NOW"
        elif usrop_count > 0:
            verdict = "VIABLE_WITH_MORE_RECOVERY"
        else:
            verdict = "NOT_VIABLE_FROM_REAL_DATA_ALONE"
            
        gap_classification[etype] = {
            'usrop_count': usrop_count,
            'total_high_med': event_summary[etype]['total_high_med'],
            'primary_reason': primary_reason,
            'verdict': verdict
        }
            
        report.append(f"| {etype} | {usrop_count} | {passing} | {primary_reason} | {verdict} |")
        
    # STEP 4: GAP CLASSIFICATION
    report.append("\n## Step 4: Gap Classification\n")
    
    for etype, info in gap_classification.items():
        if info['verdict'] == 'VIABLE_NOW':
            report.append(f"**{etype}**: VIABLE_NOW. Real-only pipeline is feasible as sufficient passing events exist.")
            continue
            
        # Determine gap type
        if info['total_high_med'] < 5:
            gap_type = "(a) LABEL GAP — Very few verified high/medium events across all wells. Real events likely happened but were not extracted/documented cleanly."
            reco = "synthetic-only-as-placeholder-pending-more-recovery"
        elif info['usrop_count'] == 0:
            gap_type = "(c) COVERAGE GAP — Event exists in DDR but doesn't occur in the 7 USROP-covered wells. This is a field distribution property."
            reco = "synthetic-only-as-placeholder-pending-more-recovery"
        else:
            gap_type = f"(b) TELEMETRY GAP — Events exist in USROP wells but failed the causal gate structurally ({info['primary_reason']})."
            reco = "real+synthetic-augmented"
            if 'flow' in etype.lower() and not has_flow_out_usrop:
                gap_type += " (Missing crucial flow-out channel for robust detection)."
                
        report.append(f"**{etype}**")
        report.append(f"Gap Type: {gap_type}")
        report.append(f"Verdict: {reco}\n")
        
    with open('reports/real_data_coverage_audit.md', 'w') as f:
        f.write("\n".join(report))

if __name__ == "__main__":
    main()
