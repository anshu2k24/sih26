#!/usr/bin/env python3
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parent.parent
TABLES_DIR = REPO_ROOT / "reports" / "tables"
FIG_DIR = REPO_ROOT / "reports" / "figures" / "events"
REPORTS_DIR = REPO_ROOT / "reports"

df_cand = pd.read_csv(TABLES_DIR / "event_candidates.csv")
df_sum = pd.read_csv(TABLES_DIR / "event_summary.csv")

# 1. Visualization
plt.figure(figsize=(10,6))
sns.barplot(data=df_sum, x='Event_Type', y='Total_Candidates', color='lightblue', label='Total')
sns.barplot(data=df_sum, x='Event_Type', y='HIGH_Conf', color='darkblue', label='HIGH Conf')
plt.xticks(rotation=45)
plt.title("Event Candidates by Type and Confidence")
plt.legend()
plt.tight_layout()
plt.savefig(FIG_DIR / "event_counts.png")
plt.close()

# Depth distribution of high conf events
high_conf = df_cand[df_cand['confidence'] == 'HIGH'].dropna(subset=['md'])
if len(high_conf) > 0:
    plt.figure(figsize=(10,6))
    sns.boxplot(data=high_conf, x='event_type', y='md', hue='event_type', legend=False)
    plt.xticks(rotation=45)
    plt.title("Depth Distribution of HIGH Confidence Events")
    plt.ylabel("Measured Depth (m)")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "event_depth_distribution.png")
    plt.close()

# Timeline for a well (e.g. 15/9-F-15)
w_df = df_cand[(df_cand['wellbore_id'] == '15/9-F-15') & (df_cand['confidence'].isin(['HIGH', 'MEDIUM']))].copy()
if len(w_df) > 0:
    w_df['date'] = pd.to_datetime(w_df['timestamp_start'].str[:10], errors='coerce')
    w_df = w_df.dropna(subset=['date']).sort_values('date')
    if len(w_df) > 0:
        plt.figure(figsize=(12, 4))
        sns.scatterplot(data=w_df, x='date', y='event_type', hue='confidence', s=100)
        plt.title("Event Timeline for 15/9-F-15")
        plt.tight_layout()
        plt.savefig(FIG_DIR / "timeline_F-15.png")
        plt.close()

# 2. NLP Extraction Feasibility MD
feasibility_md = """# NLP Event Extraction Feasibility

## 1. Feasibility Assessment
Based on an audit of the Daily Drilling Reports (DDR) text logs (`activity` and `statusInfo`), the raw text contains robust engineering terminology. 
It is **highly feasible** to extract structured information using Natural Language Processing (NLP).

### 2. Information Available
The DDR text reliably contains:
- **EVENT**: Explicitly named (e.g., "lost circulation", "stuck pipe", "kick").
- **DEPTH**: Usually embedded in the comment (e.g., "AT 2205 M") or in the metadata `md` field.
- **ACTION / MITIGATION**: Heavily documented (e.g., "PUMPED 10 M3 HI-VIS PILL", "SPOTTED LCM").
- **RESULT**: Documented as subsequent states (e.g., "CIRCULATED HOLE CLEAN", "REGAINED RETURNS").
- **FORMATION**: Occasionally mentioned, but typically implied by the depth.

### 3. Missing Information
- **CAUSE**: The fundamental root cause (e.g., "depleted zone", "fracture gradient exceeded") is often omitted in the daily operational logs, requiring inference.
- **EXACT TIMESTAMP**: Activities span hours. Pinpointing the exact minute an event occurred requires cross-referencing the WITSML high-frequency data using the `md` as a sync key.

### 4. Mitigation / Response Discovery
The text search revealed numerous operational responses:
- **Mud Loss**: Responses include "pumped LCM pill", "spotted cement plug", "reduced pump rate".
- **Stuck Pipe**: Responses include "jarring", "pumped hi-vis pill", "worked string", "spotted acid".
- **Tight Hole**: Responses include "reamed", "backreamed", "circulated bottoms up".
"""
with open(REPORTS_DIR / "event_extraction_feasibility.md", "w") as f:
    f.write(feasibility_md)

# 3. Labeling Policy MD
policy_md = """# Event Labeling Policy

## 1. Objective
Define a reproducible, strict methodology for converting noisy Daily Drilling Report (DDR) text logs into clean, binary target labels for machine learning.

## 2. Confidence Tiering
- **HIGH CONFIDENCE**: The text explicitly states the event using definitive engineering terminology (e.g., "total losses", "pipe stuck", "hole packed off"). These are the ONLY labels allowed for the positive class (1) in supervised learning.
- **MEDIUM CONFIDENCE**: The text strongly implies an event or an operational response to an event (e.g., "losses", "fishing", "reaming tight"). These must be treated as `NaN` or reviewed by an SME. Do NOT treat them as negatives.
- **LOW CONFIDENCE**: The text contains vague keywords (e.g., "cement", "returns", "torque"). These are generally safe to treat as negatives (0) unless accompanied by a higher-tier keyword, as they are often routine operations.

## 3. Ambiguity & Exclusion Rules
- **Planned Operations**: Phrases like "planned lost circulation material" or "test kick" must be excluded using negative lookahead regex or NLP context checks.
- **Historical References**: "Drilled to 3000m. No losses." -> The keyword "losses" exists but is negated. Strict boundary and negation handling must be enforced.

## 4. Duplicate & Merging Rules
- **Temporal Merging**: If multiple HIGH confidence events of the same type occur within 24 hours (e.g., across 3 consecutive `activity` entries), they are merged into a single event episode.
- **Depth Tolerance**: The `md` of the event is the minimum `md` recorded during the episode. Any WITSML ML model must predict the event prior to this exact `md`.

## 5. Required PS26121 / OIL Boundary
**IMPORTANT**: The current events extracted are from the Equinor Volve prototype dataset. They serve strictly as the architectural foundation. The exact same labeling schema, taxonomy, and confidence logic will be directly applied to the incoming OIL India (OIL) eRTMAC / WCR / DDR logs. The pipeline is completely agnostic to the operator.
"""
with open(REPORTS_DIR / "event_labeling_policy.md", "w") as f:
    f.write(policy_md)

