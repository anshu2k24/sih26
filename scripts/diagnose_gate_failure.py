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

    usrop_wells_list = usrop['well_id'].unique().tolist()
    ddr_mapped_wells = ["NO " + w for w in usrop_wells_list]

    # Filter strictly to the 7 USROP wells
    events_usrop_only = events[events['wellbore_id'].isin(ddr_mapped_wells)]

    # 1. 5 HIGH confidence mud loss events
    high_mud_loss = events_usrop_only[
        (events_usrop_only['onset_confidence'] == 'HIGH') & 
        (events_usrop_only['event_type'].str.contains('MUD_LOSS'))
    ]

    report_lines = []
    report_lines.append("# Mud Loss Data Quality Gate Diagnosis\n")
    report_lines.append("## Event-Level Analysis\n")
    
    # Table header
    report_lines.append("| Wellbore | Onset MD | Onset Timestamp | In USROP Range? | 25m Window Gaps | DDR Activity Phase/Proprietary |")
    report_lines.append("|---|---|---|---|---|---|")

    conclusions = []

    for idx, event in high_mud_loss.iterrows():
        wb = event['wellbore_id']
        well_id = wb.replace("NO ", "")
        onset_md = event['onset_md']
        ts_str = event['onset_timestamp']
        ts = parse_date(ts_str)

        # 2. USROP MD Range
        usrop_well = usrop[usrop['well_id'] == well_id]
        if usrop_well.empty:
            in_range_str = "No USROP Data"
            gaps_str = "N/A"
            min_md = np.nan
            max_md = np.nan
        else:
            min_md = usrop_well['Measured Depth m'].min()
            max_md = usrop_well['Measured Depth m'].max()
            
            # 3. Check Range
            target_md = onset_md - 25.0
            in_range = (min_md <= target_md) and (onset_md <= max_md)
            in_range_str = f"Yes (Range: {min_md:.1f}-{max_md:.1f})" if in_range else f"No (Range: {min_md:.1f}-{max_md:.1f})"
            
            # 4. Calculate Gaps
            gaps_str = "Out of Range"
            if target_md >= min_md:
                window = usrop_well[(usrop_well['Measured Depth m'] >= target_md) & (usrop_well['Measured Depth m'] <= onset_md)]
                if window.empty:
                    gaps_str = "Empty Window"
                else:
                    mds = np.sort(window['Measured Depth m'].values)
                    diffs = np.diff(mds)
                    # List gaps > 1.0m
                    large_gaps = diffs[diffs > 1.0]
                    if len(large_gaps) == 0:
                        gaps_str = "No gaps > 1m"
                    else:
                        gaps_str = ", ".join([f"{g:.1f}m" for g in np.round(large_gaps, 1)])
                        
        # 5. DDR Activity
        act_str = "Not Found"
        if pd.notna(ts):
            ddr_well = ddr[ddr['nameWellbore'] == wb]
            for _, r in ddr_well.iterrows():
                start = parse_date(r['dTimStart'])
                end = parse_date(r['dTimEnd'])
                if pd.notna(start) and pd.notna(end):
                    # Check if event falls on this day
                    if start.date() == ts.date():
                        acts = r['activity']
                        if acts is not None and len(acts) > 0:
                            found = False
                            for act in acts:
                                a_start = parse_date(act.get('dTimStart'))
                                a_end = parse_date(act.get('dTimEnd'))
                                if pd.notna(a_start) and pd.notna(a_end):
                                    if a_start <= ts <= a_end:
                                        phase = act.get('phase', '')
                                        prop = act.get('proprietaryCode', '')
                                        act_str = f"{phase} / {prop}"
                                        found = True
                                        break
                            if not found:
                                act_str = "Day found, specific time mismatch"
                        else:
                            act_str = "No Activity Array"

        report_lines.append(f"| {wb} | {onset_md:.2f} | {ts_str} | {in_range_str} | {gaps_str} | {act_str} |")
        
        # Deduce failure reason
        if not in_range:
            conclusions.append("(a) Depth-range/alignment bug (event falls outside the recorded USROP bounds).")
        elif "Empty Window" in gaps_str or sum([float(x.replace('m', '')) for x in gaps_str.split(", ")] if gaps_str != "No gaps > 1m" else []) > 10.0:
            conclusions.append("(b) Genuine sensor dropout/gaps > 10m.")
        if "drilling" not in act_str.lower():
            conclusions.append(f"(c) Event occurring during non-drilling activity ({act_str}).")


    # 6. Global Counts across 7 USROP wells
    med_unk_mud_loss = events_usrop_only[
        (events_usrop_only['onset_confidence'].isin(['MEDIUM', 'UNKNOWN'])) & 
        (events_usrop_only['event_type'].str.contains('MUD_LOSS'))
    ]
    
    other_high = events_usrop_only[
        (events_usrop_only['onset_confidence'] == 'HIGH') & 
        (~events_usrop_only['event_type'].str.contains('MUD_LOSS'))
    ]

    report_lines.append("\n## Global Context (Across 7 USROP Wells)\n")
    report_lines.append(f"- **MEDIUM/UNKNOWN Confidence Mud-Loss Events:** {len(med_unk_mud_loss)}")
    report_lines.append(f"- **HIGH Confidence OTHER Events (e.g. Stuck Pipe, Kick):** {len(other_high)}")

    report_lines.append("\n## Conclusion")
    report_lines.append("Based on the data above, the gate failures appear to be a mix of:")
    for c in list(set(conclusions)):
        report_lines.append(f"- {c}")

    with open('reports/mud_loss_gate_diagnosis.md', 'w') as f:
        f.write("\n".join(report_lines))

if __name__ == "__main__":
    main()
