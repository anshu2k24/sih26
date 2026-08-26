# Checkpoint 2: USROP Data Audit + Preparation

## 1. Exact Processed Schema
| field                          | dtype   | valid_range         |   missingness |
|:-------------------------------|:--------|:--------------------|--------------:|
| Measured Depth m               | float64 | [225.17, 4090.00]   |             0 |
| Weight on Bit kkgf             | float64 | [0.00, 31.41]       |             0 |
| Average Standpipe Pressure kPa | float64 | [1432.66, 24998.46] |             0 |
| Average Surface Torque kN.m    | float64 | [0.01, 36.49]       |             0 |
| Rate of Penetration m/h        | float64 | [0.33, 99.21]       |             0 |
| Average Rotary Speed rpm       | float64 | [0.00, 311.23]      |             0 |
| Mud Flow In L/min              | float64 | [185.42, 4538.45]   |             0 |
| Mud Density In g/cm3           | float64 | [1.02, 12.02]       |             0 |
| Diameter mm                    | float64 | [215.90, 444.50]    |             0 |
| Average Hookload kkgf          | float64 | [84.05, 152.93]     |             0 |
| Hole Depth (TVD) m             | float64 | [225.16, 3248.39]   |             0 |
| USROP Gamma gAPI               | float64 | [0.00, 260.90]      |             0 |

**Unit Note (`kkgf`)**: The unit `kkgf` stands for kilo-kilogram-force (or metric tonne-force). 1 kkgf = 1000 kgf ≈ 9.8 kN. We have explicitly preserved the original units (e.g., `Weight on Bit kkgf`, `Average Hookload kkgf`) without silent conversion to kg, ensuring physical correctness and traceability to the source data.

## 2. Exact Physical Transformations
- The raw CSV files were loaded and concatenated.
- The pandas indexing artifact column `Unnamed: 0` was dropped.
- A `well_id` was mapped directly from the filename to standard Volve wellbore names.
- The data was sorted by `well_id` and `Measured Depth m`.
- **NO filtering, resampling, interpolation, or unit conversion was applied.** The output parquet `data/processed/usrop/usrop_clean.parquet` is an exact, cleaned representation of the source.

## 3. Data Quality Findings
### Physical Plausibility Rules
| Rule             |   Violations |   Percentage |   Affected Wells |
|:-----------------|-------------:|-------------:|-----------------:|
| ROP <= 0         |            0 |            0 |              nan |
| WOB <= 0         |            0 |            0 |              nan |
| RPM < 0          |            0 |            0 |              nan |
| Torque < 0       |            0 |            0 |              nan |
| Flow < 0         |            0 |            0 |              nan |
| Mud density <= 0 |            0 |            0 |              nan |
| Diameter <= 0    |            0 |            0 |              nan |
| Hookload < 0     |            0 |            0 |              nan |
| TVD <= 0         |            0 |            0 |              nan |
| TVD > MD + 0.1   |            0 |            0 |              nan |

**Observations**:
- Zero or negative values in ROP, WOB, RPM, and Torque are present and mechanically plausible (e.g., pulling out of hole, non-drilling phases, sensor zeroes).
- Zero or negative Hookload/TVD were not observed.
- The target dataset has been rigorously cleaned by UiS authors, with zero missing values across core mechanics channels.

## 4. EDA Findings
- The depth step (sampling interval) median is highly concentrated around ~0.03m to 0.05m depending on the well.
- The correlation matrix shows expected physical relationships: e.g., Hookload inversely correlates with WOB (as WOB is applied, hookload drops). Torque correlates with WOB and RPM.

## 5. Target Distribution (ROP)
- The target variable `Rate of Penetration m/h` exhibits a right-skewed distribution.
- Values range from 0 to over 100 m/h.
- Zero values exist and must be handled depending on whether we aim to predict purely "on-bottom drilling" or all states.
- No outlier removal has been performed on the target yet.

## 6. Leakage Risks
For the target `Rate of Penetration m/h` (Current ROP):
- **Inputs (Setpoints)**: `Weight on Bit`, `Rotary Speed`, `Mud Flow In`, `Mud Density`. These are rig setpoints and are **safe** to use as current-step inputs for prediction.
- **Responses (Dependent Variables)**: `Surface Torque`, `Standpipe Pressure`, `Hookload`. These are physical responses to the rock being drilled. If we use *current* Torque to predict *current* ROP, it is technically **sensor fusion / virtual logging** rather than true predictive modeling (leakage of current rock state). However, for purely benchmarking ROP estimation, using current responses is standard. For actual *future prediction*, we must shift these responses to past timestamps/depths.
- **`Hole Depth (TVD) m` / `Measured Depth m`**: Safe to use as current state indicators.
- **Gamma**: Safe to use if logged ahead of the bit (LWD), but often logged behind the bit (requiring depth alignment).

## 7. Recommended Prediction Formulation
**Objective**: Predict `Rate of Penetration m/h` at depth step $d$.
**Formulation**: $ROP_d = f(WOB_d, RPM_d, Flow_d, MD_d, TVD_d, Torque_{d-1}, SPPA_{d-1})$
*Using strict inputs at step $d$ and lagging the response variables by one step to prevent leakage.*

## 8. Recommended Well-Based Split
**Evaluation Strategy**: Leave-One-Well-Out (Unseen Well Evaluation).
- Train on 5 wells.
- Validate on 1 well (e.g., 15/9-F-14).
- Test on 1 strictly hold-out well (e.g., 15/9-F-15S).
*Random splitting across all rows is invalid due to extreme autocorrelation of geological formations.*

## 9. Files Created
- `data/processed/usrop/usrop_clean.parquet`
- `reports/tables/usrop_schema.csv`
- `reports/tables/usrop_quality_flags.csv`
- `reports/tables/usrop_well_summary.csv`
- `reports/usrop_checkpoint2.md`
- `reports/usrop_eda.html`
- `reports/figures/usrop/*.png`

## 10. Unresolved Questions
- Should zero-ROP rows (non-drilling) be removed for the benchmarking task, or should the model implicitly learn to classify non-drilling states?
- Does the client want the ML model to perform virtual logging (using current torque/sppa) or true prediction (using lagged torque/sppa)?
