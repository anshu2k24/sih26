# USROP Dataset Verification

## 1. Source Information
- **Source URL**: `https://github.com/AndrzejTunkiel/USROP`
- **Licence**: CC BY-NC-SA 4.0 (Equinor Open Data License derivative)
- **Attribution**: Tunkiel, Sui & Wiktorski, "Reference dataset for rate of penetration benchmarking", Journal of Petroleum Science and Engineering (2021). DOI: 10.1016/j.petrol.2020.108069.

## 2. Paper Claims vs Actual Observation
| Metric | Paper Claim | Actual Observation | Match |
|---|---|---|---|
| Well Count | 7 | 7 | YES |
| Total Row Count | 198,928 | 198928 | YES |
| Attributes (Columns) | 12 | 13 | NO |
| Index | Depth-based | Depth-based (`Measured Depth m`) | YES |

## 3. Discovered Files
### USROP_A 0 N-NA_F-9_Ad.csv
- **Rows**: 13,746
- **Columns**: 13
- **MD Range**: 491.033 to 1205.999
- **Missing Values**: 0
- **Duplicate Rows**: 0
- **Median Sampling Interval**: 0.042
### USROP_A 1 N-S_F-7d.csv
- **Rows**: 6,389
- **Columns**: 13
- **MD Range**: 301.231 to 633.536
- **Missing Values**: 0
- **Duplicate Rows**: 0
- **Median Sampling Interval**: 0.051
### USROP_A 2 N-SH_F-14d.csv
- **Rows**: 47,645
- **Columns**: 13
- **MD Range**: 987.948 to 3466.033
- **Missing Values**: 0
- **Duplicate Rows**: 0
- **Median Sampling Interval**: 0.037
### USROP_A 3 N-SH-F-15d.csv
- **Rows**: 53,041
- **Columns**: 13
- **MD Range**: 1306.525 to 4065.346
- **Missing Values**: 0
- **Duplicate Rows**: 0
- **Median Sampling Interval**: 0.027
### USROP_A 4 N-SH_F-15Sd.csv
- **Rows**: 51,708
- **Columns**: 13
- **MD Range**: 1400.55 to 4090.001
- **Missing Values**: 0
- **Duplicate Rows**: 0
- **Median Sampling Interval**: 0.031
### USROP_A 5 N-SH-F-5d.csv
- **Rows**: 18,548
- **Columns**: 13
- **MD Range**: 2828.239 to 3792.2
- **Missing Values**: 0
- **Duplicate Rows**: 0
- **Median Sampling Interval**: 0.031
### USROP_A 6 N-SH_F-9d.csv
- **Rows**: 7,851
- **Columns**: 13
- **MD Range**: 225.171 to 633.536
- **Missing Values**: 0
- **Duplicate Rows**: 0
- **Median Sampling Interval**: 0.045

## 4. Exact Columns Discovered
- `Average Hookload kkgf`
- `Average Rotary Speed rpm`
- `Average Standpipe Pressure kPa`
- `Average Surface Torque kN.m`
- `Diameter mm`
- `Hole Depth (TVD) m`
- `Measured Depth m`
- `Mud Density In g/cm3`
- `Mud Flow In L/min`
- `Rate of Penetration m/h`
- `USROP Gamma gAPI`
- `Unnamed: 0`
- `Weight on Bit kkgf`
## 5. Data Quality Summary
- **Missingness**: The extracted USROP dataset has been pre-cleaned by the authors. Missingness is minimal or zero in the core mechanics columns as they were specifically interpolated/selected for ML benchmarking.
- **Suitability**: This dataset is **HIGHLY SUITABLE** for our first ML experiment. It provides the exact surface drilling parameters (WOB, RPM, Torque, ROP, SPPA) that are missing from the Daily Drilling Reports (`volve_ddr.parquet`).

## 6. Discrepancies
- Depending on the exact execution, total rows might slightly deviate if the authors updated the repo, but it should tightly align with the 198,928 samples claimed.
- Some columns might have slight name variations (e.g., 'USROP Gamma gAPI' vs 'Gamma gAPI').
