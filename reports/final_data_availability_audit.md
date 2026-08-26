# Final Data Availability Audit

## Methodology
This audit re-examined every data file in the repository, re-verified all DDR-to-USROP well identifier mappings (including sidetrack resolution), and cross-referenced every verified event episode against the actual USROP sensor depth ranges at three causal horizons (25m, 50m, 100m).

## Key Corrections from Previous Audits
1. **F-9 → F-9 A Sidetrack**: The DDR `NO 15/9-F-9` logged a `FORMATION_MUD_LOSS` event at 1083m. The USROP parent well `15/9-F-9` only covers 225–633m (surface section). The USROP sidetrack `15/9-F-9 A` covers 491–1206m, which fully contains the 1083m onset and its 25/50/100m cutoffs. This is a legitimate physical remapping (the event occurred during sidetrack drilling) and rescues 1 FML episode.
2. **F-15 A → F-15S**: The DDR `NO 15/9-F-15 A` maps to USROP `15/9-F-15S` (the sidetrack designation). This rescues 3 Tight Hole episodes (at 1467m, 2572m, 2777m).

## Local Data Files Inspected
- `data/raw/volve_ddr.parquet` (1,759 DDR reports, 22 unique wellbores)
- `data/raw/usrop/` (7 raw CSV files → 7 USROP wells)
- `data/processed/usrop/usrop_clean.parquet` (198,928 rows, 7 wells)
- `data/raw/realtime_catalog.json` (empty catalog, no additional WITSML)
- No additional XML, LAS, or alternate sensor archives found in the repository.

## USROP Sensor Coverage (Exact Depth Ranges)
| USROP Well | MD Start | MD End | Rows |
|------------|----------|--------|------|
| 15/9-F-14 | 987.9 | 3466.0 | 47,645 |
| 15/9-F-15 | 1306.5 | 4065.3 | 53,041 |
| 15/9-F-15S | 1400.5 | 4090.0 | 51,708 |
| 15/9-F-5 | 2828.2 | 3792.2 | 18,548 |
| 15/9-F-7 | 301.2 | 633.5 | 6,389 |
| 15/9-F-9 | 225.2 | 633.5 | 7,851 |
| 15/9-F-9 A | 491.0 | 1206.0 | 13,746 |

## Critical Results: Event + Sensor Coverage at 25m Horizon

### Per-Target Analysis
| Target | Verified Episodes | Valid at 25m | Distinct Wells | Wells | Meets 5-Well Gate? |
|--------|-------------------|-------------|----------------|-------|-------------------|
| FORMATION_MUD_LOSS | 17 | 4 | 2 | F-15, F-9 A | **NO** |
| Tight Hole | 39 | 4 | 2 | F-15S, F-5 | **NO** |
| Pack-off | 18 | 2 | 1 | F-15 | **NO** |
| Stuck Pipe | 12 | 0 | 0 | — | **NO** |
| Equipment Failure | 34 | 3 | 2 | F-14, F-5 | **NO** |
| UNIFIED_DRILLING_RISK | 86 | 10 | 4 | F-15, F-15S, F-5, F-9 A | **NO** |
| **ALL_EVENTS** | **129** | **14** | **5** | **F-14, F-15, F-15S, F-5, F-9 A** | **YES** |

### The 5-Well Gate Decision
No single event type passes the 5-well requirement. The only configuration that achieves exactly 5 distinct wells is the `ALL_EVENTS` combined target, which merges heterogeneous event types (FML, Tight Hole, Pack-off, Equipment Failure, Cementing Loss).

## Scientific Assessment of the ALL_EVENTS Target

### Arguments FOR proceeding:
- The 5-well gate is mathematically satisfied (14 episodes, 5 wells).
- All 5 wells have real USROP high-frequency sensor data at the required causal cutoffs.
- The events are all verified, non-fabricated DDR episodes.
- A unified "any-drilling-risk" binary classifier is operationally meaningful: engineers benefit from an early warning of *any* upcoming issue.

### Arguments AGAINST proceeding:
- The event types are mechanistically different. A Mud Loss (formation response) and an Equipment Failure (mechanical) have different physical signatures. Combining them assumes a shared predictive signal, which is unproven.
- F-14 only contributes Equipment Failure episodes. F-9 A only contributes 1 FML episode. The per-well class balance is fragile.
- With only 14 positive episodes across 5 wells, each LOWO fold will have very few test positives (often just 1–3), making per-fold metrics statistically unreliable.
- F-15 and F-15S are the parent well and sidetrack of the same physical well structure. Treating them as independent wells in LOWO may overestimate generalization.

## ML READINESS DECISION

### FORMATION_MUD_LOSS (original target): **ML BLOCKED — REAL DATA INSUFFICIENT**
Only 2 wells with valid sensor overlap. Cannot perform LOWO.

### ALL_EVENTS (unified target): **BORDERLINE — SCIENTIFICALLY FRAGILE**
The 5-well gate is technically satisfied, but:
- The combined target mixes mechanistically distinct event types.
- F-15/F-15S independence is questionable (same well structure).
- Per-fold test counts are extremely low.

**Recommendation:** This experiment CAN be run as an exploratory/proof-of-concept investigation under the explicit caveat that the results are scientifically fragile and should not be presented as production-grade generalization metrics. The experiment is valuable for validating the pipeline architecture and identifying whether any sensor-based predictive signal exists at all.

If the user authorizes this exploratory experiment, it must be clearly labeled:
*"EXPLORATORY — 5-well ALL_EVENTS unified target, results are indicative only, not production-grade."*
