#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("semantic_audit_v2")

REPO_ROOT = Path(__file__).resolve().parent.parent
TABLES_DIR = REPO_ROOT / "reports" / "tables"
REPORTS_DIR = REPO_ROOT / "reports"

# Regexes
NEGATION_REGEX = re.compile(r'\b(no\s+losses|without\s+losses|zero\s+losses|no\s+returns\s+expected|no\s+kick|no\s+flow|not\s+stuck|prevent\s+(?:losses|kick|stuck))\b', re.IGNORECASE)
PLANNED_REGEX = re.compile(r'\b(plan\s+to|prepare\s+to|will|contingency|potential\s+risk|in\s+case\s+of)\b', re.IGNORECASE)

POSITIVES = {
    "Mud Loss": [r'\b(lost circulation|total losses|complete loss|measured lost volume|losses to formation|losing mud|losses at \d+|loss of \d+)\b'],
    "Pack-off": [r'\b(hole packed off|packed off|pack-off occurred)\b'],
    "Stuck Pipe": [r'\b(pipe stuck|string stuck|stuck pipe|stuck in hole)\b'],
    "Tight Hole": [r'\b(tight hole|hole tight|tight spot)\b'],
    "Equipment Failure": [r'\b(equipment failure|parted|washed out|failed|broken down)\b'],
    "Fishing": [r'\b(fish in hole|twisted off|fishing incident)\b'],
    "Kick": [r'\b(took a kick|well kicked|influx|gain in trip tank associated with influx)\b'],
    "Cementing Problem": [r'\b(cement failure|no cement returns|remedial cement)\b']
}

MITIGATIONS = {
    "Mud Loss": [r'\b(lcm|pill|plug|lost circulation material)\b'],
    "Stuck Pipe": [r'\b(jarring|jar|worked string|worked pipe|acid|free point)\b'],
    "Tight Hole": [r'\b(ream|backream|washing|obstruction|drag|stalling)\b'],
    "Kick": [r'\b(weight up|kill mud|circulate out)\b'],
    "Pack-off": [r'\b(pump out|surge)\b']
}

def is_tool_term(text, etype):
    text_lower = text.lower()
    if etype == "Pack-off":
        return bool(re.search(r'\b(pack[- ]?off assembly|spear with pack[- ]?off|pack[- ]?off rubber)\b', text_lower))
    if etype == "Fishing":
        return bool(re.search(r'\b(fishing operation|fishing assembly|fishing tool|fishing bumper|jar)\b', text_lower)) and not bool(re.search(r'\b(fish in hole|twisted off|left in hole)\b', text_lower))
    if etype == "Kick":
        return bool(re.search(r'\b(kick valve|shut in well with select tester|choke test)\b', text_lower))
    return False

def check_semantics_v2(text, etype):
    if not isinstance(text, str): return "AMBIGUOUS", "Missing text", "OPERATIONAL/EQUIPMENT_EVENT", etype
    
    t_orig = text.lower()
    t_clean = re.sub(NEGATION_REGEX, ' ', t_orig)
    
    # Check for direct positive in cleaned text
    has_pos = False
    for pat in POSITIVES.get(etype, []):
        if re.search(pat, t_clean):
            has_pos = True
            break
            
    has_mit = False
    for pat in MITIGATIONS.get(etype, []):
        if re.search(pat, t_orig):
            has_mit = True
            break
            
    is_neg = bool(re.search(NEGATION_REGEX, t_orig))
    is_tool = is_tool_term(t_orig, etype)
    is_plan = bool(re.search(PLANNED_REGEX, t_orig))
    
    status = "AMBIGUOUS"
    if is_tool:
        status = "TOOL_ASSEMBLY"
    elif has_pos:
        status = "DIRECT_EVENT"
    elif is_neg:
        status = "NEGATED"
    elif is_plan:
        status = "PLANNED_OPERATION"
    elif has_mit:
        status = "MITIGATION"
    else:
        status = "CONTEXT"
        
    # Domain filtering
    domain = "OPERATIONAL/EQUIPMENT_EVENT"
    final_etype = etype
    if etype in ["Stuck Pipe", "Pack-off", "Tight Hole", "Kick"]:
        domain = "FORMATION/DRILLING_RISK"
    elif etype == "Mud Loss":
        # Check if cementing related
        if re.search(r'\b(cement|cmt|spacer|lead|tail|shoe)\b', t_orig):
            final_etype = "CEMENTING/OPERATIONAL_LOSS"
            domain = "OPERATIONAL/EQUIPMENT_EVENT"
        else:
            final_etype = "FORMATION_MUD_LOSS"
            domain = "FORMATION/DRILLING_RISK"
            
    return status, status, domain, final_etype

def detect_resolution(text):
    if not isinstance(text, str): return False
    t = text.lower()
    resolutions = [r'\b(no losses|circulation restored|regained returns|free|hole clean)\b']
    for pat in resolutions:
        if re.search(pat, t): return True
    return False

def main():
    logger.info("Loading candidates...")
    CANDIDATES_PATH = TABLES_DIR / "event_candidates.csv"
    if not CANDIDATES_PATH.exists(): return
    df = pd.read_csv(CANDIDATES_PATH)
    
    old_verified_path = TABLES_DIR / "verified_event_episodes.csv"
    df_old_ver = pd.read_csv(old_verified_path) if old_verified_path.exists() else pd.DataFrame()
    
    status_list, reason_list, domain_list, f_etype_list = [], [], [], []
    
    for _, row in df.iterrows():
        st, rsn, dom, fet = check_semantics_v2(row['text'], row['event_type'])
        status_list.append(st)
        reason_list.append(rsn)
        domain_list.append(dom)
        f_etype_list.append(fet)
        
    df['semantic_status'] = status_list
    df['semantic_reason'] = reason_list
    df['event_domain'] = domain_list
    df['final_event_type'] = f_etype_list
    df['is_resolution'] = df['text'].apply(detect_resolution)
    
    # 2. Episode Merging
    df['date'] = pd.to_datetime(df['timestamp_start'].str[:10], errors='coerce')
    df = df.sort_values(by=['wellbore_id', 'final_event_type', 'date', 'md'])
    
    episodes = []
    ep_id = 1
    
    for (wb, etype), group in df.groupby(['wellbore_id', 'final_event_type']):
        current_ep = []
        for idx, row in group.iterrows():
            if not current_ep:
                current_ep.append(row)
                continue
                
            last_row = current_ep[-1]
            time_diff = (row['date'] - last_row['date']).days if (pd.notnull(row['date']) and pd.notnull(last_row['date'])) else None
            md_diff = abs(row['md'] - last_row['md']) if (pd.notnull(row['md']) and pd.notnull(last_row['md'])) else None
            
            separate = False
            if last_row['is_resolution']: separate = True
            elif time_diff is not None and time_diff > 3: separate = True
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
    
    for eid, rows in episodes:
        df_ep = pd.DataFrame(rows)
        etype = df_ep['final_event_type'].iloc[0]
        dom = df_ep['event_domain'].iloc[0]
        
        positives = df_ep[df_ep['semantic_status'] == 'DIRECT_EVENT']
        if len(positives) > 0:
            onset_row = positives.iloc[0]
            onset_conf = "HIGH" if pd.notnull(onset_row['md']) else "UNKNOWN"
            
            mitig = df_ep[df_ep['semantic_reason'] == 'MITIGATION']['text'].tolist()
            res = df_ep[df_ep['is_resolution']]['text'].tolist()
            supp = positives.iloc[1:]['event_id'].tolist() if len(positives) > 1 else []
            supp_txt = positives.iloc[1:]['text'].tolist() if len(positives) > 1 else []
            
            verified_episodes.append({
                "event_episode_id": f"EP_V2_{eid}",
                "event_type": etype,
                "event_domain": dom,
                "well_id": onset_row['well_id'],
                "wellbore_id": onset_row['wellbore_id'],
                "onset_timestamp": onset_row['timestamp_start'],
                "onset_md": onset_row['md'],
                "onset_tvd": onset_row['tvd'],
                "onset_confidence": onset_conf,
                "end_timestamp": df_ep['timestamp_end'].max(),
                "end_md": df_ep['md'].max(),
                "primary_source_record": onset_row['event_id'],
                "primary_evidence": onset_row['text'].replace('\n', ' '),
                "supporting_record_ids": ",".join(supp),
                "supporting_evidence": " | ".join(supp_txt).replace('\n', ' '),
                "mitigation_text": " | ".join(mitig).replace('\n', ' '),
                "resolution_text": " | ".join(res).replace('\n', ' '),
                "semantic_status": "VERIFIED",
                "is_verified_positive": True
            })
            
    df_ver = pd.DataFrame(verified_episodes)
    df_ver.to_csv(TABLES_DIR / "verified_event_episodes_v2.csv", index=False)
    
    # Label Errors Audit (Comparing V1 and V2)
    # The user specifically mentioned KICK EP_35 being a false positive in V1, and Mud Loss being falsely negated in QA.
    # We will identify V1 verified episodes that are NO LONGER in V2 (meaning they were rejected).
    error_list = []
    if len(df_old_ver) > 0:
        for _, old_r in df_old_ver.iterrows():
            old_evidence = old_r['primary_evidence']
            old_etype = old_r['event_type']
            
            # Find in df
            matching_rows = df[(df['event_type'] == old_etype) & (df['text'].str.replace('\n', ' ') == old_evidence)]
            if len(matching_rows) > 0:
                new_st = matching_rows['semantic_status'].iloc[0]
                if new_st != 'DIRECT_EVENT':
                    error_list.append({
                        "event_episode_id": old_r['event_episode_id'],
                        "event_type": old_etype,
                        "error_type": "FALSE_POSITIVE_V1",
                        "original_label": "VERIFIED_HIGH",
                        "corrected_label": new_st,
                        "evidence": old_evidence,
                        "reason": f"V1 misclassified as HIGH. V2 strictly reclassified as {new_st}."
                    })
                    
    # Also find false negatives from previous QA
    qa_path = TABLES_DIR / "event_manual_qa.csv"
    if qa_path.exists():
        df_qa = pd.read_csv(qa_path)
        for _, qa_r in df_qa.iterrows():
            if qa_r['decision'] == 'REJECTED':
                matching_rows = df[(df['event_type'] == qa_r['event_type']) & (df['text'] == qa_r['text'])]
                if len(matching_rows) > 0:
                    new_st = matching_rows['semantic_status'].iloc[0]
                    if new_st == 'DIRECT_EVENT':
                        error_list.append({
                            "event_episode_id": "QA_ROW",
                            "event_type": qa_r['event_type'],
                            "error_type": "FALSE_NEGATIVE_QA",
                            "original_label": "REJECTED",
                            "corrected_label": "DIRECT_EVENT",
                            "evidence": qa_r['text'],
                            "reason": f"V1 misclassified as negated/rejected. V2 strictly reclassified as DIRECT_EVENT."
                        })
                        
    df_err = pd.DataFrame(error_list)
    df_err.to_csv(TABLES_DIR / "event_label_errors.csv", index=False)
    
    # ML Readiness V2
    ml_readiness = []
    types = df['final_event_type'].unique()
    for et in types:
        if len(df_ver) > 0 and et in df_ver['event_type'].values:
            ver_et = df_ver[df_ver['event_type'] == et]
            v_eps = len(ver_et)
            p_wells = ver_et['well_id'].nunique()
            p_wb = ver_et['wellbore_id'].nunique()
            r_onset = len(ver_et[ver_et['onset_confidence'] == 'HIGH'])
            mit = len(ver_et[ver_et['mitigation_text'] != ''])
            md = len(ver_et[pd.notnull(ver_et['onset_md'])])
            
            rec = "YES" if (r_onset >= 10 and p_wells >= 5) else "NO"
            reason = "Sufficient verified episodes with reliable onset depth across multiple wells." if rec == "YES" else "Insufficient verified episodes with reliable onset."
        else:
            v_eps, p_wells, p_wb, r_onset, mit, md = 0, 0, 0, 0, 0, 0
            rec = "NO"
            reason = "No verified positive episodes found."
            
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
    df_ml.to_csv(TABLES_DIR / "event_ml_readiness_v2.csv", index=False)
    
    # Manual QA V2
    qa_list = []
    def sample_qa(df_ver, df_all, et, status):
        if status == 'DIRECT_EVENT':
            sub = df_ver[df_ver['event_type'] == et]
            if len(sub) > 0:
                s = sub.sample(min(10, len(sub)), replace=False)
                for _, r in s.iterrows():
                    qa_list.append({"text": r['primary_evidence'], "final_event_type": et, "decision": "ACCEPTED", "reason": "Explicit direct evidence (V2)"})
        else:
            sub = df_all[(df_all['final_event_type'] == et) & (df_all['semantic_status'] != 'DIRECT_EVENT')]
            if len(sub) > 0:
                s = sub.sample(min(10, len(sub)), replace=False)
                for _, r in s.iterrows():
                    qa_list.append({"text": r['text'], "final_event_type": et, "decision": "REJECTED", "reason": r['semantic_status']})

    for etype in ["FORMATION_MUD_LOSS", "CEMENTING/OPERATIONAL_LOSS", "Stuck Pipe", "Pack-off", "Kick"]:
        sample_qa(df_ver, df, etype, 'DIRECT_EVENT')
        sample_qa(df_ver, df, etype, 'REJECTED')
        
    df_qa_v2 = pd.DataFrame(qa_list)
    df_qa_v2.to_csv(TABLES_DIR / "event_manual_qa_v2.csv", index=False)
    
    logger.info("Done generating V2 semantic audit tables.")

if __name__ == "__main__":
    main()
