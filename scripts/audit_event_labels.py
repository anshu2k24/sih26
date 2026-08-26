#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TABLES_DIR = REPO_ROOT / "reports" / "tables"
CANDIDATES_PATH = TABLES_DIR / "event_candidates.csv"

def get_negation_regex():
    return re.compile(r'\b(no\s+losses|without\s+losses|prevent|no\s+kick|no\s+flow|not\s+stuck)\b', re.IGNORECASE)

def get_planned_regex():
    return re.compile(r'\b(plan\s+to|prepare\s+to|will|contingency|potential|risk\s+of)\b', re.IGNORECASE)

def get_mitigation_keywords():
    return {
        "Mud Loss": ["lcm", "pill", "plug", "lost circulation material"],
        "Stuck Pipe": ["jarring", "jar", "worked string", "acid", "free point"],
        "Tight Hole": ["ream", "backream", "washing"],
        "Kick": ["weight up", "kill mud", "circulate out"],
        "Pack-off": ["pump out", "surge"]
    }

def process_text(text, event_type, conf):
    if not isinstance(text, str): return False, False, False
    t_lower = text.lower()
    
    # Negation
    neg_regex = get_negation_regex()
    is_negated = bool(neg_regex.search(t_lower))
    
    # Planned
    plan_regex = get_planned_regex()
    is_planned = bool(plan_regex.search(t_lower))
    
    # Mitigation Only
    is_mitig_only = False
    if conf != "HIGH":  # If it's HIGH, we have the root problem stated.
        mits = get_mitigation_keywords().get(event_type, [])
        has_mitig = any(m in t_lower for m in mits)
        if has_mitig:
            is_mitig_only = True
            
    return is_negated, is_planned, is_mitig_only

def main():
    if not CANDIDATES_PATH.exists():
        print("No candidates found")
        return
        
    df = pd.read_csv(CANDIDATES_PATH)
    
    # Apply NLP checks
    neg_list, plan_list, mitig_list = [], [], []
    for _, row in df.iterrows():
        n, p, m = process_text(row['text'], row['event_type'], row['confidence'])
        neg_list.append(n)
        plan_list.append(p)
        mitig_list.append(m)
        
    df['is_negated'] = neg_list
    df['is_planned'] = plan_list
    df['is_mitig_only'] = mitig_list
    
    # Context only - LOW confidence that isn't mitigated, planned, or negated
    df['is_context_only'] = (df['confidence'] == 'LOW') & (~df['is_negated']) & (~df['is_planned']) & (~df['is_mitig_only'])
    
    # Episode Merging
    # We group by wellbore_id and event_type. If events are within 2 days or 100m, they are the same episode.
    df['date'] = pd.to_datetime(df['timestamp_start'].str[:10], errors='coerce')
    df = df.sort_values(by=['wellbore_id', 'event_type', 'date', 'md'])
    
    episodes = []
    episode_id_counter = 1
    
    for (wb, etype), group in df.groupby(['wellbore_id', 'event_type']):
        current_ep = []
        for idx, row in group.iterrows():
            if not current_ep:
                current_ep.append(row)
            else:
                last_row = current_ep[-1]
                # Check proximity
                time_diff = pd.NaT
                if pd.notnull(row['date']) and pd.notnull(last_row['date']):
                    time_diff = (row['date'] - last_row['date']).days
                    
                md_diff = np.nan
                if pd.notnull(row['md']) and pd.notnull(last_row['md']):
                    md_diff = abs(row['md'] - last_row['md'])
                    
                same_ep = False
                if pd.notnull(time_diff) and time_diff <= 2: same_ep = True
                elif pd.notnull(md_diff) and md_diff <= 100: same_ep = True
                elif pd.isnull(time_diff) and pd.isnull(md_diff): same_ep = True # Group unknowns
                
                if same_ep:
                    current_ep.append(row)
                else:
                    # Finalize current episode
                    episodes.append((episode_id_counter, current_ep))
                    episode_id_counter += 1
                    current_ep = [row]
        
        if current_ep:
            episodes.append((episode_id_counter, current_ep))
            episode_id_counter += 1
            
    # Compile episode summary
    ep_summary_list = []
    
    # Add episode ID to original df for easy counting
    df['episode_id'] = np.nan
    for e_id, ep_rows in episodes:
        for r in ep_rows:
            df.loc[df['event_id'] == r['event_id'], 'episode_id'] = e_id
            
    # Now build the Event Summary table
    audit_summary = []
    
    for etype in df['event_type'].unique():
        sub = df[df['event_type'] == etype]
        
        tot_c = len(sub)
        h_c = len(sub[sub['confidence'] == 'HIGH'])
        m_c = len(sub[sub['confidence'] == 'MEDIUM'])
        l_c = len(sub[sub['confidence'] == 'LOW'])
        u_wells = sub['well_id'].nunique()
        u_wellbores = sub['wellbore_id'].nunique()
        
        neg_c = sub['is_negated'].sum()
        mit_c = sub['is_mitig_only'].sum()
        ctx_c = sub['is_context_only'].sum()
        pln_c = sub['is_planned'].sum()
        
        # Unique episodes
        ep_count = sub['episode_id'].nunique()
        dups = tot_c - ep_count
        
        # High confidence episodes
        high_eps = sub[sub['confidence'] == 'HIGH']['episode_id'].unique()
        verified_pos = len(high_eps)
        u_high_wells = sub[sub['episode_id'].isin(high_eps)]['well_id'].nunique()
        
        high_mds = sub[sub['episode_id'].isin(high_eps)]['md'].dropna()
        h_min = high_mds.min() if len(high_mds) > 0 else np.nan
        h_max = high_mds.max() if len(high_mds) > 0 else np.nan
        
        # Samples
        pos_sample = sub[(sub['confidence'] == 'HIGH') & (~sub['is_negated'])]['text'].dropna().head(2).tolist()
        neg_sample = sub[sub['is_negated']]['text'].dropna().head(2).tolist()
        mit_sample = sub[sub['is_mitig_only']]['text'].dropna().head(2).tolist()
        
        audit_summary.append({
            "event_type": etype,
            "total_candidate_rows": tot_c,
            "HIGH_rows": h_c,
            "MEDIUM_rows": m_c,
            "LOW_rows": l_c,
            "unique_wells": u_wells,
            "unique_wellbores": u_wellbores,
            "verified_positive_episodes": verified_pos,
            "negated_rows": neg_c,
            "mitigation_only_rows": mit_c,
            "context_only_rows": ctx_c,
            "planned_operation_rows": pln_c,
            "duplicate_or_same_episode_rows": dups,
            "estimated_independent_episodes": ep_count,
            "unique_high_confidence_onset_wells": u_high_wells,
            "high_confidence_onset_depth_min": h_min,
            "high_confidence_onset_depth_max": h_max,
            "sample_positive_texts": " | ".join(pos_sample).replace('\n', ' '),
            "sample_negated_texts": " | ".join(neg_sample).replace('\n', ' '),
            "sample_mitigation_only_texts": " | ".join(mit_sample).replace('\n', ' ')
        })
        
    df_audit = pd.DataFrame(audit_summary)
    df_audit.to_csv(TABLES_DIR / "event_label_audit_summary.csv", index=False)
    
    # ----------------------------------------------------
    # Table 2: Event Episode Examples
    # ----------------------------------------------------
    # We want 30-50 rows total across strongest types. (Mud Loss, Stuck Pipe, Pack-off, Tight Hole)
    strong_types = ['Mud Loss', 'Stuck Pipe', 'Pack-off', 'Tight Hole', 'Equipment Failure']
    ep_examples = []
    
    for e_id, ep_rows in episodes:
        df_ep = pd.DataFrame(ep_rows)
        etype = df_ep['event_type'].iloc[0]
        if etype not in strong_types: continue
        
        # we want a mix of high conf and others. Let's just pick high conf ones mostly.
        # But we also need some negated or mitigation ones.
        conf = "HIGH" if (df_ep['confidence'] == 'HIGH').any() else "MEDIUM"
        if conf == "MEDIUM" and not (df_ep['is_mitig_only']).any() and len(ep_examples) > 40:
            continue
            
        if len(ep_examples) >= 50:
            break
            
        is_verified = conf == "HIGH" and not (df_ep['is_negated']).any()
        
        primary_ev = df_ep[df_ep['confidence'] == conf]['text'].iloc[0] if len(df_ep[df_ep['confidence'] == conf]) > 0 else df_ep['text'].iloc[0]
        supp_ev = " | ".join(df_ep[df_ep['text'] != primary_ev]['text'].dropna().head(2).tolist())
        mitig_text = " | ".join(df_ep[df_ep['is_mitig_only']]['text'].dropna().tolist())
        
        onset_md = df_ep['md'].min()
        onset_ts = df_ep['timestamp_start'].min()
        
        ep_examples.append({
            "event_episode_id": f"EP_{e_id}",
            "event_type": etype,
            "well_id": df_ep['well_id'].iloc[0],
            "wellbore_id": df_ep['wellbore_id'].iloc[0],
            "onset_md": onset_md,
            "onset_timestamp": onset_ts,
            "confidence": conf,
            "evidence_type": "Direct" if conf == "HIGH" else ("Mitigation" if df_ep['is_mitig_only'].any() else "Context"),
            "source_record_ids": ",".join(df_ep['event_id'].astype(str)),
            "primary_evidence": primary_ev.replace('\n', ' ') if pd.notnull(primary_ev) else "",
            "supporting_evidence": supp_ev.replace('\n', ' '),
            "mitigation_text": mitig_text.replace('\n', ' '),
            "is_verified_positive": is_verified,
            "merge_reason": "Time<=2d or MD<=100m" if len(df_ep) > 1 else "Single",
            "negation_detected": df_ep['is_negated'].any()
        })
        
    df_examples = pd.DataFrame(ep_examples)
    df_examples.to_csv(TABLES_DIR / "event_episode_examples.csv", index=False)
    
if __name__ == "__main__":
    main()
