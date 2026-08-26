#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
from pathlib import Path
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("event_extraction")

REPO_ROOT = Path(__file__).resolve().parent.parent
DDR_PATH = REPO_ROOT / "data" / "raw" / "volve_ddr.parquet"
REPORTS_DIR = REPO_ROOT / "reports"
TABLES_DIR = REPORTS_DIR / "tables"
FIG_DIR = REPORTS_DIR / "figures" / "events"
for d in [TABLES_DIR, FIG_DIR]: d.mkdir(parents=True, exist_ok=True)

TAXONOMY = {
    "Mud Loss": {
        "HIGH": ["lost circulation", "total losses", "no returns", "complete loss"],
        "MEDIUM": ["partial losses", "mud loss", "seepage losses", "lcm pill", "lcm"],
        "LOW": ["losses", "loss", "returns"]
    },
    "Kick": {
        "HIGH": ["well kicked", "took a kick", "blowout"],
        "MEDIUM": ["influx", "well flowing", "shut in well", "well control"],
        "LOW": ["kick", "gain", "flow check"]
    },
    "Stuck Pipe": {
        "HIGH": ["stuck pipe", "pipe stuck", "string stuck"],
        "MEDIUM": ["unable to move", "unable to rotate", "stuck"],
        "LOW": ["overpull", "drag", "jarring"]
    },
    "Tight Hole": {
        "HIGH": ["tight hole", "hole tight"],
        "MEDIUM": ["reaming tight", "reaming"],
        "LOW": ["tight"]
    },
    "Pack-off": {
        "HIGH": ["pack-off", "packed off", "hole packed off"],
        "MEDIUM": ["pack off"],
        "LOW": ["pack"]
    },
    "Fishing": {
        "HIGH": ["fishing operations", "fish in hole", "twisted off"],
        "MEDIUM": ["fishing", "milling fish", "catch fish"],
        "LOW": ["fish", "mill"]
    },
    "Equipment Failure": {
        "HIGH": ["equipment failure", "parted", "washed out"],
        "MEDIUM": ["failure", "broken", "repair", "rig repair"],
        "LOW": ["failed", "leak", "replace"]
    },
    "Cementing Problem": {
        "HIGH": ["cement failure", "no cement returns"],
        "MEDIUM": ["cementing issue", "squeeze job"],
        "LOW": ["cement", "cmt"]
    }
}

def check_event(text):
    if not isinstance(text, str): return None, None
    text_lower = text.lower()
    
    # Priority check: HIGH -> MEDIUM -> LOW
    candidates = []
    
    for event_type, levels in TAXONOMY.items():
        found = False
        for level in ["HIGH", "MEDIUM", "LOW"]:
            if found: break
            for kw in levels[level]:
                if kw in text_lower:
                    # Specific boundaries checking
                    # If kw is "losses", make sure it's not "glosses" - simple \b boundary
                    if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                        candidates.append((event_type, level, kw))
                        found = True
                        break
                        
    if not candidates: return None, None
    
    # Sort candidates by confidence
    level_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    candidates.sort(key=lambda x: level_rank[x[1]], reverse=True)
    
    # Just return the top confidence event found
    best = candidates[0]
    return best[0], best[1]

def main():
    logger.info("Loading DDR parquet...")
    df = pd.read_parquet(DDR_PATH)
    
    candidates_list = []
    
    logger.info("Extracting Activity events...")
    for idx, row in df.iterrows():
        well = row.get('nameWell', 'Unknown')
        wellbore = row.get('nameWellbore', 'Unknown')
        
        # Parse activity
        activities = row.get('activity')
        if isinstance(activities, np.ndarray) or isinstance(activities, list):
            for act in activities:
                if not isinstance(act, dict): continue
                text = act.get('comments', '')
                code = act.get('proprietaryCode', '')
                phase = act.get('phase', '')
                dTimStart = act.get('dTimStart', '')
                dTimEnd = act.get('dTimEnd', '')
                md = act.get('md', np.nan)
                
                combined_text = f"{code} | {text}"
                event_type, conf = check_event(combined_text)
                
                if event_type:
                    candidates_list.append({
                        "event_id": f"ACT_{len(candidates_list)}",
                        "well_id": well,
                        "wellbore_id": wellbore,
                        "event_type": event_type,
                        "confidence": conf,
                        "source_object": "activity",
                        "source_field": "comments",
                        "text": text,
                        "md": float(md) if md and md != '-999.99' else np.nan,
                        "tvd": np.nan,
                        "timestamp_start": dTimStart,
                        "timestamp_end": dTimEnd,
                        "raw_code": code,
                        "evidence_reason": "Regex Match"
                    })
                    
        # Parse statusInfo
        statusInfo = row.get('statusInfo')
        if isinstance(statusInfo, np.ndarray) or isinstance(statusInfo, list):
            for stat in statusInfo:
                if not isinstance(stat, dict): continue
                text = stat.get('sum24Hr', '')
                forecast = stat.get('forecast24Hr', '')
                md = stat.get('md', np.nan)
                tvd = stat.get('tvd', np.nan)
                dTim = stat.get('dTim', '')
                
                combined_text = f"{text} | {forecast}"
                event_type, conf = check_event(combined_text)
                
                if event_type:
                    candidates_list.append({
                        "event_id": f"STAT_{len(candidates_list)}",
                        "well_id": well,
                        "wellbore_id": wellbore,
                        "event_type": event_type,
                        "confidence": conf,
                        "source_object": "statusInfo",
                        "source_field": "sum24Hr",
                        "text": text,
                        "md": float(md) if md and md != '-999.99' else np.nan,
                        "tvd": float(tvd) if tvd and tvd != '-999.99' else np.nan,
                        "timestamp_start": dTim,
                        "timestamp_end": dTim,
                        "raw_code": "",
                        "evidence_reason": "Regex Match"
                    })
                    
    df_cand = pd.DataFrame(candidates_list)
    df_cand.to_csv(TABLES_DIR / "event_candidates.csv", index=False)
    
    # Quality Audit
    logger.info("Performing label quality audit...")
    summary = []
    if len(df_cand) > 0:
        for etype in df_cand['event_type'].unique():
            sub = df_cand[df_cand['event_type'] == etype]
            total = len(sub)
            high = len(sub[sub['confidence'] == 'HIGH'])
            med = len(sub[sub['confidence'] == 'MEDIUM'])
            low = len(sub[sub['confidence'] == 'LOW'])
            wells = sub['well_id'].nunique()
            wellbores = sub['wellbore_id'].nunique()
            
            # Simple dedup heuristic: same well, same type, same day
            # If timestamp exists, we could check. We'll just count total for now.
            summary.append({
                "Event_Type": etype,
                "Total_Candidates": total,
                "HIGH_Conf": high,
                "MED_Conf": med,
                "LOW_Conf": low,
                "Unique_Wells": wells,
                "Unique_Wellbores": wellbores
            })
            
    df_sum = pd.DataFrame(summary)
    df_sum.to_csv(TABLES_DIR / "event_summary.csv", index=False)
    
    # Save a sample of high confidence events
    if len(df_cand) > 0:
        high_conf = df_cand[df_cand['confidence'] == 'HIGH']
        high_conf.head(50).to_csv(TABLES_DIR / "event_evidence_samples.csv", index=False)
    
    logger.info("Done extracting events.")

if __name__ == "__main__":
    main()
