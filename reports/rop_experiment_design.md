# Rate of Penetration (ROP) Experiment Design (Revised)

## 1. Prediction Horizon Analysis
**Objective**: Predict ROP at a future depth $d + \Delta$ using only information available at or before depth $d$.

### Horizon Sensitivity Analysis Plan (Tolerance: ±0.1m)
| well       |   total_samples |   h_0.5m_count |   h_0.5m_pct |   h_1.0m_count |   h_1.0m_pct |   h_2.0m_count |   h_2.0m_pct |   h_5.0m_count |   h_5.0m_pct |   h_10.0m_count |   h_10.0m_pct |
|:-----------|----------------:|---------------:|-------------:|---------------:|-------------:|---------------:|-------------:|---------------:|-------------:|----------------:|--------------:|
| 15/9-F-14  |           47645 |          43160 |        90.59 |          44247 |        92.87 |          43090 |        90.44 |          43739 |        91.8  |           43410 |         91.11 |
| 15/9-F-15  |           53041 |          50807 |        95.79 |          50728 |        95.64 |          49721 |        93.74 |          49161 |        92.68 |           48411 |         91.27 |
| 15/9-F-15S |           51708 |          46590 |        90.1  |          47048 |        90.99 |          45988 |        88.94 |          45802 |        88.58 |           45068 |         87.16 |
| 15/9-F-5   |           18548 |          17089 |        92.13 |          17316 |        93.36 |          16547 |        89.21 |          15953 |        86.01 |           15148 |         81.67 |
| 15/9-F-7   |            6389 |           6271 |        98.15 |           6218 |        97.32 |           6150 |        96.26 |           6034 |        94.44 |            5865 |         91.8  |
| 15/9-F-9   |            7851 |           7499 |        95.52 |           7557 |        96.26 |           7397 |        94.22 |           7394 |        94.18 |            7238 |         92.19 |
| 15/9-F-9 A |           13746 |          13073 |        95.1  |          13280 |        96.61 |          12866 |        93.6  |          13049 |        94.93 |           12832 |         93.35 |

**Plan**: We will not prematurely assume an optimal horizon. Instead, we will conduct a sensitivity analysis across $\Delta$ = [0.5, 1.0, 2.0, 5.0, 10.0] meters. 
The final recommended primary horizon will be justified using a combination of:
1. **Coverage**: The proportion of valid training/testing target samples available.
2. **Predictive Difficulty**: Evaluated by measuring the degradation of the persistence baseline as $\Delta$ increases.
3. **Engineering Relevance**: The operational value of predicting across the chosen distance (e.g., compensating for BHA length vs predicting broad lithological changes).

## 2. Feature Availability & Leakage Rules

**Strict Rule**: NO FUTURE INFORMATION may enter the feature vector. For predicting $ROP_{d+\Delta}$, only features at depth $\le d$ can be used.

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
To emulate real-world operational predictive support (historical wells $\rightarrow$ unseen target well), we will execute a **Leave-One-Well-Out (LOWO)** cross-validation scheme across all 7 wells:
- Each held-out well must be completely absent from training.
- Per-well and aggregate metrics will be reported.
- (A single fixed train/validation/test split may be kept for a final demonstration, but performance claims will rely entirely on the LOWO evaluation).

## 5. Baselines & Model Candidates

### Baselines (Pre-ML)
1. **Naive Baseline (Persistence)**: $ROP_{d+\Delta} = ROP_d$
   *This is a SERIOUS benchmark. ML models must demonstrate meaningful improvement over persistence to be considered valuable.*
2. **Mean/Median Baseline**: $ROP_{d+\Delta} = \text{mean/median}(ROP_{train})$
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
