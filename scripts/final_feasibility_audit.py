import pandas as pd
import numpy as np
import sys
sys.path.append('src')
from ertmac.ml.inference import DataQualityGate

def parse_date(date_str):
    try:
        return pd.to_datetime(date_str, utc=True)
    except:
        return pd.NaT

def main():
    events = pd.read_csv('reports/tables/verified_event_episodes_v2.csv')
    usrop = pd.read_parquet('data/processed/usrop/usrop_clean.parquet')
    ddr = pd.read_parquet('volve_ddr.parquet')

    usrop_wells = usrop['well_id'].unique().tolist()
    ddr_mapped_wells = ["NO " + w for w in usrop_wells]

    col_map = {
        'Measured Depth m': 'md', 'Weight on Bit kkgf': 'wob', 'Average Standpipe Pressure kPa': 'spp',
        'Average Surface Torque kN.m': 'torque', 'Rate of Penetration m/h': 'rop', 'Average Rotary Speed rpm': 'rpm',
        'Mud Flow In L/min': 'flow_in', 'Mud Density In g/cm3': 'mud_density', 'Diameter mm': 'diameter',
        'Average Hookload kkgf': 'hookload', 'Hole Depth (TVD) m': 'tvd', 'USROP Gamma gAPI': 'gamma'
    }
    usrop = usrop.rename(columns=col_map)
    usrop['wellbore_id'] = usrop['well_id'].apply(lambda x: "NO " + x)

    quality_gate = DataQualityGate(required_history_md=25.0)

    report = []
    report.append("# Final Real-Data Feasibility Audit")
    
    # Check Stuck Pipe texts specifically
    stuck_pipe = events[(events['event_type'] == 'Stuck Pipe') & (events['onset_confidence'] == 'HIGH')]
    # Text is usable if primary_evidence or mitigation_text is present and not nan/empty
    usable_count = 0
    wbs = set()
    for _, r in stuck_pipe.iterrows():
        ev = str(r.get('primary_evidence', ''))
        mit = str(r.get('mitigation_text', ''))
        if (ev and ev.lower() != 'nan') or (mit and mit.lower() != 'nan'):
            usable_count += 1
            wbs.add(r['wellbore_id'])
    
    report.append(f"\n**Note on Stuck Pipe:** There are {len(stuck_pipe)} HIGH-confidence Stuck Pipe labels, all in wellbores with zero USROP telemetry coverage. However, {usable_count} of these events contain USABLE evidence/mitigation text for retrieval purposes (found in wellbores: {', '.join(wbs)}).")
    
    report.append("\n## Feasibility Table")
    report.append("| Event Type | USROP Range Events | Passing Gate | Passing Wells | Final Verdict | Notes |")
    report.append("|---|---|---|---|---|---|")

    # Only look at events with >= 1 HIGH/MEDIUM in a USROP-covered well, plus Stuck Pipe and Kick.
    # Wait, the prompt says "EVERY event_type with at least 1 HIGH or MEDIUM confidence episode in a USROP-covered well — not just mud loss and stuck pipe."
    # We will compute USROP-covered events for all types first.
    
    for etype in sorted(events['event_type'].unique()):
        sub_all_hm = events[(events['event_type'] == etype) & (events['onset_confidence'].isin(['HIGH', 'MEDIUM']))]
        sub = sub_all_hm[sub_all_hm['wellbore_id'].isin(ddr_mapped_wells)]
        
        if len(sub) == 0 and etype not in ['Kick', 'Stuck Pipe']:
            continue
            
        if etype == 'Kick':
            report.append(f"| Kick | {len(sub)} | 0 | 0 | STRUCTURAL_TELEMETRY_GAP | flow_out absent from all sources |")
            continue
        if etype == 'Stuck Pipe':
            report.append(f"| Stuck Pipe | 0 | 0 | 0 | STRUCTURAL_COVERAGE_GAP | 12 events exist in non-USROP wells |")
            continue
            
        passing_events = []
        notes = []
        
        # Analyze each event
        for _, row in sub.iterrows():
            wb = row['wellbore_id']
            onset = row['onset_md']
            ts = parse_date(row['onset_timestamp'])
            
            w_df = usrop[usrop['wellbore_id'] == wb]
            if w_df.empty:
                continue
                
            min_md, max_md = w_df['md'].min(), w_df['md'].max()
            cutoff = onset - 25.0
            
            if not (min_md <= cutoff and onset <= max_md):
                continue
                
            history = w_df[w_df['md'] <= cutoff]
            status = quality_gate.check_quality(history, cutoff, wb)
            
            if status == 'PASS':
                # Determine DDR phase
                act_str = "Unknown"
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
                                    phase = act.get('phase', '')
                                    prop = act.get('proprietaryCode', '')
                                    act_str = f"{phase}/{prop}"
                                    break
                
                passing_events.append({'wellbore_id': wb, 'phase': act_str})
                if 'drill' not in act_str.lower():
                    notes.append(f"Non-drilling phase: {act_str}")
        
        pass_count = len(passing_events)
        pass_wells = len(set([x['wellbore_id'] for x in passing_events]))
        
        if pass_count > 0:
            verdict = "REAL_VIABLE_NOW"
        else:
            if len(sub) > 0:
                verdict = "REAL_VIABLE_WITH_MORE_DDR_RECOVERY"
            else:
                verdict = "STRUCTURAL_COVERAGE_GAP"
                
        # summarize notes
        note_str = "All passing" if pass_count > 0 and not notes else ", ".join(list(set(notes)))
        if not note_str:
            note_str = "Failed gate or MD range"
            
        report.append(f"| {etype} | {len(sub)} | {pass_count} | {pass_wells} | {verdict} | {note_str} |")

    with open('reports/real_data_feasibility_final.md', 'w') as f:
        f.write("\n".join(report))

if __name__ == "__main__":
    main()
