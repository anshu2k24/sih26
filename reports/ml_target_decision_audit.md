# Final ML Target Decision Audit

## Executive Summary
This audit evaluated the 14 valid episodes across 5 distinct USROP sensor wells discovered during the coverage check. The critical question was whether these 5 physical wells constitute 5 *independent* geological folds suitable for Leave-One-Well-Out (LOWO) scientific evaluation.

## Independence Analysis (Parent vs. Sidetrack)
In LOWO, if an algorithm trains on a parent well and predicts on its sidetrack, this is **not** an independent test. They share the same surface location, conductor, upper hole geology, and physical rig environment. 

A rigorous audit of the 5 USROP wells revealed:
- `15/9-F-15` (Parent) and `15/9-F-15S` (Sidetrack) are the same well structure. They **must** be grouped into a single `F-15_GROUP`.
- `15/9-F-9 A` is a sidetrack. It forms `F-9_GROUP`.
- `15/9-F-14` is independent (`F-14`).
- `15/9-F-5` is independent (`F-5`).

**Conclusion:** The 5 USROP wells represent only **4 independent well groups**.

## Candidate Formulation Comparison

### A. FORMATION_MUD_LOSS
- **Positives:** 4 episodes
- **Independent Well Groups:** 2 (`F-15_GROUP`, `F-9_GROUP`)
- **Feasibility of LOWO:** IMPOSSIBLE (Fails minimum 5-group gate).
- **Major Weakness:** Cannot scientifically evaluate generalization.

### B. UNIFIED_DRILLING_RISK (Mud Loss + Tight Hole + Pack-off + Stuck Pipe)
- **Positives:** 10 episodes
- **Independent Well Groups:** 3 (`F-15_GROUP`, `F-5`, `F-9_GROUP`)
- **Feasibility of LOWO:** IMPOSSIBLE (Fails minimum 5-group gate).
- **Major Weakness:** Still falls short of the rigorous multi-well requirement.

### C. ALL_EVENTS (Unified Risk + Equipment Failure + Cementing Loss)
- **Positives:** 14 episodes
- **Independent Well Groups:** 4 (`F-14`, `F-15_GROUP`, `F-5`, `F-9_GROUP`)
- **Feasibility of LOWO:** IMPOSSIBLE (Fails minimum 5-group gate).
- **Major Weakness:** By grouping parent and sidetrack wells to prevent leakage, the number of independent folds drops to 4. Even if we proceeded, mixing mechanical Equipment Failures with geological Mud Losses assumes a shared predictive signal, which is physically unjustifiable.

## FINAL DECISION

**ML BLOCKED — NEED REAL DATA**

### Justification
Under rigorous scientific scrutiny, the Volve dataset simply does not possess enough independent overlapping well telemetry to support a valid supervised learning experiment. 

We explicitly refuse to:
- Lower the 5-well gate to 4 just to force a result.
- Treat `F-15` and `F-15S` as independent when they are geologically coupled.
- Synthesize fake telemetry.

The ML architecture and readiness gates are fully operational. The pipeline is securely waiting for the real OIL/eRTMAC dataset.
