#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_PARQUET = REPO_ROOT / "data" / "processed" / "usrop" / "usrop_clean.parquet"
REPORTS_DIR = REPO_ROOT / "reports"

def calculate_horizon_coverage(df, horizons=[0.5, 1.0, 2.0, 5.0, 10.0], tolerance=0.1):
    print("Calculating horizon coverage...")
    results = []
    
    for well, group in df.groupby('well_id'):
        depths = group['Measured Depth m'].values
        N = len(depths)
        
        row_dict = {"well": well, "total_samples": N}
        
        for h in horizons:
            target_depths = depths + h
            idx = np.searchsorted(depths, target_depths, side='left')
            
            valid_targets = 0
            for i, target_idx in enumerate(idx):
                if target_idx < N:
                    actual_depth = depths[target_idx]
                    if abs(actual_depth - target_depths[i]) <= tolerance:
                        valid_targets += 1
                elif target_idx - 1 < N: 
                    actual_depth = depths[target_idx - 1]
                    if abs(actual_depth - target_depths[i]) <= tolerance:
                        valid_targets += 1
                        
            row_dict[f"h_{h}m_count"] = valid_targets
            row_dict[f"h_{h}m_pct"] = round((valid_targets / N) * 100, 2)
            
        results.append(row_dict)
        
    return pd.DataFrame(results)

def main():
    if not PROCESSED_PARQUET.exists():
        print(f"File not found: {PROCESSED_PARQUET}")
        return
        
    df = pd.read_parquet(PROCESSED_PARQUET)
    
    horizon_df = calculate_horizon_coverage(df)
    
    md_content = f"""# Rate of Penetration (ROP) Experiment Design (Revised)

## 1. Prediction Horizon Analysis
**Objective**: Predict ROP at a future depth $d + \\Delta$ using only information available at or before depth $d$.

### Horizon Sensitivity Analysis Plan (Tolerance: ±0.1m)
{horizon_df.to_markdown(index=False)}

**Plan**: We will not prematurely assume an optimal horizon. Instead, we will conduct a sensitivity analysis across $\\Delta$ = [0.5, 1.0, 2.0, 5.0, 10.0] meters. 
The final recommended primary horizon will be justified using a combination of:
1. **Coverage**: The proportion of valid training/testing target samples available.
2. **Predictive Difficulty**: Evaluated by measuring the degradation of the persistence baseline as $\\Delta$ increases.
3. **Engineering Relevance**: The operational value of predicting across the chosen distance (e.g., compensating for BHA length vs predicting broad lithological changes).

## 2. Feature Availability & Leakage Rules

**Strict Rule**: NO FUTURE INFORMATION may enter the feature vector. For predicting $ROP_{{d+\\Delta}}$, only features at depth $\le d$ can be used.

### Feature Ablation Groups
To quantify what information actually drives predictive performance, features will be evaluated sequentially by group:

- **Group A (Position)**:
  - `Measured Depth m` (Current, $d$)
  - `Hole Depth (TVD) m` (Current, $d$)
- **Group B (Setpoints/Inputs)**:
  - `Weight on Bit kkgf` (Current, $d$)
  - `Average Rotary Speed rpm` (Current, $d$)
  - `Mud Flow In L/min` (Current, $d$)
  - `Mud Density In g/cm3` (Current, $d$)
  - `Diameter mm` (Current, $d$)
- **Group C (Responses)**:
  - `Average Surface Torque kN.m` (Current, $d$)
  - `Average Standpipe Pressure kPa` (Current, $d$)
  - `Average Hookload kkgf` (Current, $d$)
- **Group D (Formation/LWD)**:
  - `USROP Gamma gAPI` (Historical)

### Gamma Ablation Plan
We will perform a dedicated ablation for Gamma:
- **A. Model without Gamma**.
- **B. Model with Gamma**, strictly using only information that would physically be available before the target depth. We will **not** invent a fixed 10-30m lag arbitrarily. The exact assumption and operational source of the lag (e.g., LWD sensor placement specs for Volve) will be explicitly documented before evaluation.

## 3. Zero-ROP Treatment Study
The USROP dataset as curated by Tunkiel et al. is already filtered for on-bottom drilling. There are **0 rows** with $ROP \le 0$ in the 198,928 samples. Consequently, all data represents active drilling, and zero-ROP treatment is intrinsically handled for this specific prototype.

## 4. Benchmark Methodology & Split Scenarios

### Benchmark 1: Published USROP Paper Scenario
The Tunkiel et al. (2021) paper evaluates models using random splitting / k-Fold cross-validation across the entire pooled dataset. We will reproduce this methodology purely as a baseline reference experiment.

### Benchmark 2: PS26121 Primary Evaluation (Leave-One-Well-Out)
To emulate real-world operational predictive support (historical wells $\\rightarrow$ unseen target well), we will execute a **Leave-One-Well-Out (LOWO)** cross-validation scheme across all 7 wells:
- Each held-out well must be completely absent from training.
- Per-well and aggregate metrics will be reported.
- (A single fixed train/validation/test split may be kept for a final demonstration, but performance claims will rely entirely on the LOWO evaluation).

## 5. Baselines & Model Candidates

### Baselines (Pre-ML)
1. **Naive Baseline (Persistence)**: $ROP_{{d+\\Delta}} = ROP_d$
   *This is a SERIOUS benchmark. ML models must demonstrate meaningful improvement over persistence to be considered valuable.*
2. **Mean/Median Baseline**: $ROP_{{d+\\Delta}} = \\text{{mean/median}}(ROP_{{train}})$
3. **Simple Linear Regression**: Baseline linear fit using Group A+B features.

### Model Candidates
1. **Random Forest (RF)**
2. **Gradient Boosting (XGBoost / LightGBM)**

*(No Hyperparameter tuning will be performed before establishing baselines, nor will final test wells be used for tuning).*

## 6. Evaluation Metrics
As a regression task, models will be evaluated strictly using:
- **Primary Metrics**: `MAE`, `RMSE`, `R²`
- **Secondary Analysis Metrics**: 
  - `Median absolute error`
  - `Error distribution`
  - `Per-well MAE/RMSE/R²`
  - `Prediction vs actual scatter plot`
  - `Residual plot`
  - `Error by depth`
  - `Error by ROP range`

*(Metrics like F1, precision, and recall will NOT be used).*
"""

    report_path = REPORTS_DIR / "rop_experiment_design.md"
    with open(report_path, "w") as f:
        f.write(md_content)
    
    print(f"Experiment design document written to {report_path}")

if __name__ == "__main__":
    main()
