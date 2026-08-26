#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("semantic_audit")

REPO_ROOT = Path(__file__).resolve().parent.parent
TABLES_DIR = REPO_ROOT / "reports" / "tables"
REPORTS_DIR = REPO_ROOT / "reports"
for d in [TABLES_DIR, REPORTS_DIR]: d.mkdir(parents=True, exist_ok=True)
CANDIDATES_PATH = TABLES_DIR / "event_candidates.csv"

def is_tool_term(text, etype):
    text_lower = text.lower()
    if etype == "Pack-off":
        return bool(re.search(r'\b(pack[- ]?off assembly|spear with pack[- ]?off|pack[- ]?off rubber)\b', text_lower))
    if etype == "Fishing":
        return bool(re.search(r'\b(fishing operation|fishing assembly|fishing tool|fishing bumper|jar)\b', text_lower)) and not bool(re.search(r'\b(fish in hole|twisted off|left in hole)\b', text_lower))
    return False

def check_semantics(text, etype):
    if not isinstance(text, str): return "UNKNOWN", "Missing text"
    t = text.lower()
    
    # 1. Negation
    if re.search(r'\b(no\s+losses|without\s+losses|no\s+returns\s+expected|no\s+kick|no\s+flow|not\s+stuck)\b', t):
        return "REJECTED", "NEGATED"
        
    # 2. Planned
    if re.search(r'\b(plan\s+to|prepare\s+to|will|contingency|potential\s+risk|in\s+case\s+of)\b', t):
        return "REJECTED", "PLANNED_OPERATION"
        
    # 3. Tool / Assembly term (e.g. "pack-off assembly")
    if is_tool_term(t, etype):
        return "REJECTED", "TOOL_OR_ASSEMBLY_TERM"
        
    # 4. Mitigation only (e.g. "pumped lcm", "jarring") vs Direct Evidence ("lost circulation", "pipe stuck")
    # Define exact positive signatures per type
    positives = {
        "Mud Loss": [r'\b(lost circulation|total losses|complete loss|measured lost volume|losses to formation)\b'],
        "Pack-off": [r'\b(hole packed off|packed off|pack-off occurred)\b'],
        "Stuck Pipe": [r'\b(pipe stuck|string stuck|stuck pipe|stuck in hole)\b'],
        "Tight Hole": [r'\b(tight hole|hole tight|tight spot)\b'],
        "Equipment Failure": [r'\b(equipment failure|parted|washed out|failed|broken down)\b'],
        "Fishing": [r'\b(fish in hole|twisted off|fishing incident)\b'],
        "Kick": [r'\b(took a kick|well kicked|well flowing|shut in well)\b'],
        "Cementing Problem": [r'\b(cement failure|no cement returns|remedial cement)\b']
    }
    
    mitigations = {
        "Mud Loss": [r'\b(lcm|pill|plug|lost circulation material)\b'],
        "Stuck Pipe": [r'\b(jarring|jar|worked string|worked pipe|acid|free point)\b'],
        "Tight Hole": [r'\b(ream|backream|washing|obstruction|drag|stalling)\b'],
        "Kick": [r'\b(weight up|kill mud|circulate out)\b'],
        "Pack-off": [r'\b(pump out|surge)\b']
    }
    
    has_pos = False
    for pat in positives.get(etype, []):
        if re.search(pat, t):
            has_pos = True
            break
            
    has_mit = False
    for pat in mitigations.get(etype, []):
        if re.search(pat, t):
            has_mit = True
            break
            
    if has_pos:
        return "ACCEPTED", "DIRECT_EVIDENCE"
        
    if has_mit:
        return "REJECTED", "MITIGATION_ONLY"
        
    # If no explicit positive and no explicit mitigation, it might just be contextual keyword matching from step 1
    # Check if there is a medium/low contextual keyword
    return "REJECTED", "CONTEXT_ONLY"

def detect_resolution(text, etype):
    if not isinstance(text, str): return False
    t = text.lower()
    resolutions = [r'\b(no losses|circulation restored|regained returns|free|hole clean)\b']
    for pat in resolutions:
        if re.search(pat, t): return True
    return False

def main():
    logger.info("Loading candidates...")
    if not CANDIDATES_PATH.exists(): return
    df = pd.read_csv(CANDIDATES_PATH)
    
    # 1. Evaluate every row semantically
    status_list = []
    reason_list = []
    
    for _, row in df.iterrows():
        st, rsn = check_semantics(row['text'], row['event_type'])
        status_list.append(st)
        reason_list.append(rsn)
        
    df['semantic_status'] = status_list
    df['semantic_reason'] = reason_list
    df['is_resolution'] = df.apply(lambda r: detect_resolution(r['text'], r['event_type']), axis=1)
    
    # 2. Episode Merging
    df['date'] = pd.to_datetime(df['timestamp_start'].str[:10], errors='coerce')
    df = df.sort_values(by=['wellbore_id', 'event_type', 'date', 'md'])
    
    episodes = []
    ep_id = 1
    
    for (wb, etype), group in df.groupby(['wellbore_id', 'event_type']):
        current_ep = []
        for idx, row in group.iterrows():
            if not current_ep:
                current_ep.append(row)
                continue
                
            last_row = current_ep[-1]
            time_diff = (row['date'] - last_row['date']).days if (pd.notnull(row['date']) and pd.notnull(last_row['date'])) else None
            md_diff = abs(row['md'] - last_row['md']) if (pd.notnull(row['md']) and pd.notnull(last_row['md'])) else None
            
            # Semantic separation conditions
            separate = False
            # If a resolution occurred in the previous row, separate
            if last_row['is_resolution']: separate = True
            # If huge time jump
            elif time_diff is not None and time_diff > 3: separate = True
            # If huge depth jump
            elif md_diff is not None and md_diff > 500: separate = True
            
            if separate:
                episodes.append((ep_id, current_ep))
                ep_id += 1
                current_ep = [row]
            else:
                current_ep.append(row)
                
        if current_ep:
            episodes.append((ep_id, current_ep))
            ep_id += 1
            
    # 3. Process Episodes
    verified_episodes = []
    rejected_episodes = []
    
    for eid, rows in episodes:
        df_ep = pd.DataFrame(rows)
        etype = df_ep['event_type'].iloc[0]
        
        # Identify onset (first DIRECT_EVIDENCE)
        positives = df_ep[df_ep['semantic_status'] == 'ACCEPTED']
        if len(positives) > 0:
            onset_row = positives.iloc[0]
            onset_id = onset_row['event_id']
            onset_ts = onset_row['timestamp_start']
            onset_md = onset_row['md']
            onset_tvd = onset_row['tvd']
            onset_conf = "HIGH" if pd.notnull(onset_md) else "UNKNOWN"
            
            mitig = df_ep[df_ep['semantic_reason'] == 'MITIGATION_ONLY']['text'].tolist()
            res = df_ep[df_ep['is_resolution']]['text'].tolist()
            supp = positives.iloc[1:]['event_id'].tolist() if len(positives) > 1 else []
            supp_txt = positives.iloc[1:]['text'].tolist() if len(positives) > 1 else []
            
            verified_episodes.append({
                "event_episode_id": f"EP_{eid}",
                "event_type": etype,
                "well_id": onset_row['well_id'],
                "wellbore_id": onset_row['wellbore_id'],
                "onset_timestamp": onset_ts,
                "onset_md": onset_md,
                "onset_tvd": onset_tvd,
                "onset_confidence": onset_conf,
                "end_timestamp": df_ep['timestamp_end'].max(),
                "end_md": df_ep['md'].max(),
                "primary_source_record": onset_id,
                "primary_evidence": onset_row['text'].replace('\n', ' '),
                "supporting_record_ids": ",".join(supp),
                "supporting_evidence": " | ".join(supp_txt).replace('\n', ' '),
                "mitigation_text": " | ".join(mitig).replace('\n', ' '),
                "resolution_text": " | ".join(res).replace('\n', ' '),
                "semantic_status": "VERIFIED",
                "is_verified_positive": True
            })
        else:
            # Episode has NO positive evidence -> rejected
            reason = df_ep['semantic_reason'].iloc[0] # Grab first reason
            rejected_episodes.append({
                "source_record_ids": ",".join(df_ep['event_id'].tolist()),
                "candidate_event_type": etype,
                "reason_rejected": "No direct positive evidence found in episode",
                "rejection_category": reason
            })
            
    df_ver = pd.DataFrame(verified_episodes)
    df_ver.to_csv(TABLES_DIR / "verified_event_episodes.csv", index=False)
    
    df_rej = pd.DataFrame(rejected_episodes)
    df_rej.to_csv(TABLES_DIR / "rejected_event_episodes.csv", index=False)
    
    # 4. ML Readiness Table
    ml_readiness = []
    types = df['event_type'].unique()
    for et in types:
        if len(df_ver) > 0 and et in df_ver['event_type'].values:
            ver_et = df_ver[df_ver['event_type'] == et]
            v_eps = len(ver_et)
            p_wells = ver_et['well_id'].nunique()
            p_wb = ver_et['wellbore_id'].nunique()
            r_onset = len(ver_et[ver_et['onset_confidence'] == 'HIGH'])
            mit = len(ver_et[ver_et['mitigation_text'] != ''])
            md = len(ver_et[pd.notnull(ver_et['onset_md'])])
            
            # Recommendation logic
            rec = "YES" if (r_onset >= 10 and p_wells >= 5) else "NO"
            reason = "Sufficient verified episodes with reliable onset depth across multiple wells." if rec == "YES" else "Insufficient verified episodes with reliable onset across diverse wells."
        else:
            v_eps, p_wells, p_wb, r_onset, mit, md = 0, 0, 0, 0, 0, 0
            rec = "NO"
            reason = "No verified positive episodes found after strict semantic filtering."
            
        ml_readiness.append({
            "event_type": et,
            "verified_episodes": v_eps,
            "positive_wells": p_wells,
            "positive_wellbores": p_wb,
            "episodes_with_reliable_onset": r_onset,
            "episodes_with_mitigation": mit,
            "episodes_with_depth": md,
            "recommended_for_ml": rec,
            "reason": reason
        })
        
    df_ml = pd.DataFrame(ml_readiness)
    df_ml.to_csv(TABLES_DIR / "event_ml_readiness.csv", index=False)
    
    # 5. Manual QA
    qa_list = []
    def sample_qa(df, et, cat, status):
        # sample verified
        if status == 'ACCEPTED':
            sub = df_ver[df_ver['event_type'] == et]
            if len(sub) > 0:
                s = sub.sample(min(10, len(sub)), replace=False)
                for _, r in s.iterrows():
                    qa_list.append({"text": r['primary_evidence'], "event_type": et, "decision": "ACCEPTED", "reason": "Explicit direct evidence"})
        else:
            # sample rejected from raw rows
            sub = df[(df['event_type'] == et) & (df['semantic_status'] == 'REJECTED')]
            if len(sub) > 0:
                s = sub.sample(min(10, len(sub)), replace=False)
                for _, r in s.iterrows():
                    qa_list.append({"text": r['text'], "event_type": et, "decision": "REJECTED", "reason": r['semantic_reason']})

    sample_qa(df, 'Mud Loss', 'Mud Loss', 'ACCEPTED')
    sample_qa(df, 'Mud Loss', 'Mud Loss', 'REJECTED')
    sample_qa(df, 'Stuck Pipe', 'Stuck Pipe', 'ACCEPTED')
    sample_qa(df, 'Stuck Pipe', 'Stuck Pipe', 'REJECTED')
    sample_qa(df, 'Pack-off', 'Pack-off', 'ACCEPTED')
    sample_qa(df, 'Pack-off', 'Pack-off', 'REJECTED')
    
    df_qa = pd.DataFrame(qa_list)
    df_qa.to_csv(TABLES_DIR / "event_manual_qa.csv", index=False)
    
    # 6. Event Taxonomy MD
    taxonomy_md = """# Event Taxonomy & Semantics

## 1. MUD LOSS
- **Positive**: Actual loss / lost returns / losses to formation / measured lost volume. (e.g. `lost circulation`, `total losses`)
- **Negative**: "no losses", routine circulation, "losses" mentioned historically without an active event.

## 2. PACK-OFF
- **Positive**: "hole packed off", "packed off", etc. describing actual wellbore restriction.
- **Negative**: "pack-off assembly", "casing spear with pack-off" (Tool/Assembly terms).

## 3. STUCK PIPE
- **Positive**: "pipe stuck", "string stuck".
- **Negative**: "high drag", "overpull", "jarring", "worked pipe" (unless accompanied by explicit stuck condition). These are mitigations or contexts, not explicitly the stuck state.

## 4. TIGHT HOLE
- **Positive**: explicit tight-hole condition ("tight hole", "hole tight").
- **Negative**: "reaming", "obstruction", "drag", "stalling".

## 5. FISHING
- **Positive**: `FISHING_INCIDENT` (e.g. "twisted off", "fish in hole").
- **Negative**: `FISHING_OPERATION` (e.g. "fishing operation", "jar"). Fishing tools do not equal new fishing events.

## 6. EQUIPMENT FAILURE
- **Positive**: Explicit equipment/tool failure ("broken down", "parted", "washed out").
- **Negative**: Routine maintenance, repair, testing.

## 7. CEMENTING PROBLEM
- **Positive**: Explicit cementing failure ("cement failure", "no cement returns").
- **Negative**: Routine cementing operation.

## 8. KICK
- **Positive**: Explicit well-control evidence ("took a kick", "well kicked").
- **Negative**: "kick" used in other context, or routine flow checks.
"""
    with open(REPORTS_DIR / "event_taxonomy.md", "w") as f:
        f.write(taxonomy_md)

    logger.info("Done generating semantic audit tables.")

if __name__ == "__main__":
    main()
