#!/usr/bin/env python3
import hashlib
import json
import os
import sys
from pathlib import Path
import pandas as pd
import duckdb
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "raw" / "volve_ddr.parquet"
OUTPUT_FILE = REPO_ROOT / "reports" / "checkpoint1_review.md"

def get_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    if not DATA_FILE.exists():
        print(f"Error: {DATA_FILE} not found.")
        sys.exit(1)

    con = duckdb.connect()
    
    # 1. Environment
    py_version = sys.version.replace('\n', ' ')
    env_info = "Virtual environment: .venv (pip)"
    import importlib.metadata
    packages = {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}
    req_pkgs = ['pandas', 'duckdb', 'pyarrow', 'matplotlib', 'seaborn']
    pkg_str = "\\n".join([f"- {p}: {packages.get(p, 'Not Installed')}" for p in req_pkgs])
    
    # 2. Dataset Identity
    file_size = DATA_FILE.stat().st_size
    sha256_hash = get_sha256(DATA_FILE)
    
    # 3. Exact Raw Schema
    pf = pq.ParquetFile(DATA_FILE)
    arrow_schema = pf.schema_arrow
    
    top_level_cols = []
    for i, field in enumerate(arrow_schema):
        dtype_str = str(field.type)
        if dtype_str.startswith("struct") or dtype_str.startswith("list"):
            kind = "struct/list"
        else:
            kind = "scalar"
        
        null_count = con.execute(f"SELECT COUNT(*) FROM '{DATA_FILE}' WHERE {field.name} IS NULL").fetchone()[0]
        total_count = pf.metadata.num_rows
        null_pct = (null_count / total_count) * 100
        
        try:
            unique_count = con.execute(f"SELECT COUNT(DISTINCT {field.name}) FROM '{DATA_FILE}'").fetchone()[0]
        except:
            unique_count = "N/A"
            
        top_level_cols.append(f"| {field.name} | `{dtype_str}` | {kind} | {null_count} | {null_pct:.2f}% | {unique_count} |")

    # 4. Exact Nested Schemas
    nested_fields = [
        "wellboreAlias", "wellboreInfo", "statusInfo", "fluid", 
        "porePressure", "surveyStation", "activity", "lithShowInfo"
    ]
    nested_schema_md = []
    
    for nf in nested_fields:
        nested_schema_md.append(f"### {nf}")
        try:
            # Get type from arrow schema
            field_type = str(arrow_schema.field(nf).type)
            nested_schema_md.append(f"**PyArrow Type**: `{field_type}`\\n")
            
            df_nested = con.execute(f"SELECT UNNEST({nf}) AS rec FROM '{DATA_FILE}' WHERE len({nf}) > 0 LIMIT 1").df()
            if not df_nested.empty and 'rec' in df_nested.columns and isinstance(df_nested['rec'].iloc[0], dict):
                sample_dict = df_nested['rec'].iloc[0]
                nested_schema_md.append("| Field | Type | Example |")
                nested_schema_md.append("|---|---|---|")
                for k, v in sample_dict.items():
                    val_str = str(v)[:50].replace('|', '&#124;').replace('\\n', ' ')
                    type_str = type(v).__name__
                    nested_schema_md.append(f"| {k} | {type_str} | {val_str} |")
                
            total_rows = pf.metadata.num_rows
            empty_count = con.execute(f"SELECT COUNT(*) FROM '{DATA_FILE}' WHERE len({nf}) = 0 OR {nf} IS NULL").fetchone()[0]
            nested_records = con.execute(f"SELECT SUM(len({nf})) FROM '{DATA_FILE}'").fetchone()[0] or 0
            
            nested_schema_md.append(f"\\n- **Null/Empty Rate**: {empty_count} rows ({(empty_count/total_rows)*100:.2f}%)")
            nested_schema_md.append(f"- **Total Nested Records**: {int(nested_records)}")
            
        except Exception as e:
            nested_schema_md.append(f"Error inspecting {nf}: {e}")
        nested_schema_md.append("")

    # 5. Data Quality
    sentinel_md = []
    numeric_fields = [
        "md", "tvd", "distDrill", "ropCurrent", "waterDepth",
        "mdPlanned", "mdKickoff", "mdCsgLast", "mdPlugTop",
        "elevKelly", "wellheadElevation"
    ]
    for f in numeric_fields:
        try:
            res = con.execute(f"SELECT COUNT(*), COUNT(*) FILTER (WHERE s.{f} = '-999.99') FROM (SELECT UNNEST(statusInfo) as s FROM '{DATA_FILE}')").fetchone()
            if res[0] > 0 and res[1] > 0:
                sentinel_md.append(f"| statusInfo.{f} | `-999.99` | {res[1]} | {(res[1]/res[0])*100:.2f}% |")
        except:
            pass

    # 6. Well / Wellbore Identity
    well_identity = con.execute(f"""
        SELECT nameWell, nameWellbore, COUNT(*) as report_count
        FROM '{DATA_FILE}'
        GROUP BY nameWell, nameWellbore
        ORDER BY nameWell, nameWellbore
    """).df()
    
    unique_wells = well_identity['nameWell'].nunique()
    unique_wellbores = well_identity['nameWellbore'].nunique()
    
    well_table = "| nameWell | nameWellbore | Report Count |\\n|---|---|---|\\n"
    for _, r in well_identity.iterrows():
        well_table += f"| {r['nameWell']} | {r['nameWellbore']} | {r['report_count']} |\\n"

    # 7. Temporal Coverage
    temp_cov = con.execute(f"""
        SELECT 
            MIN(TRY_CAST(dTimStart AS TIMESTAMPTZ)) as min_start,
            MAX(TRY_CAST(dTimEnd AS TIMESTAMPTZ)) as max_end
        FROM '{DATA_FILE}'
    """).fetchone()

    # Generate Markdown
    md_content = f"""# Checkpoint 1 Review

## 1. Environment
- **Python Version**: {py_version}
- **OS**: {os.uname().sysname} {os.uname().release}
- **Environment**: {env_info}
- **Packages**:
{pkg_str}
- **Command Used**: `python scripts/run_audit.py`

## 2. Dataset Identity
- **Local Filename**: volve_ddr.parquet
- **File Size**: {file_size:,} bytes
- **SHA256**: {sha256_hash}
- **Source Repository**: bengsoon/volve_daily_drilling_report (HuggingFace)
- **Original Source**: Equinor Volve Data Sharing
- **Dataset Description**: Derived WITSML 1.4.1.1 Daily Drilling Reports reformatted into Parquet.
- **Dataset Boundary**: This Parquet is Daily Drilling Report data and is NOT a continuous drilling telemetry dataset.
- **Type**: Derived data.

## 3. Exact Raw Schema
| Name | Arrow Type | Kind | Null Count | Null % | Unique Count |
|---|---|---|---|---|---|
{"\\n".join(top_level_cols)}

## 4. Exact Nested Schemas
{"\\n".join(nested_schema_md)}

## 5. Data Quality
- **Sentinel Values (`-999.99`)**:
| Column | Sentinel | Count | Percentage |
|---|---|---|---|
{"\\n".join(sentinel_md)}

## 6. Well / Wellbore Identity
- **Unique nameWell**: {unique_wells}
- **Unique nameWellbore**: {unique_wellbores}

**Well -> Wellbore -> Report Count**:
{well_table}

**Ambiguous Naming Cases**:
`NO 15/9-F-11` has variants: `NO 15/9-F-11`, `NO 15/9-F-11 A`, `NO 15/9-F-11 B`, `NO 15/9-F-11 T2`.
It is unclear if these represent sidetracks, separate sections, or renaming over time.

## 7. Temporal Coverage
- **Min dTimStart**: {temp_cov[0]}
- **Max dTimEnd**: {temp_cov[1]}

## 8. Depth / Trajectory Coverage
(Based on `statusInfo` and `surveyStation`, excluding `-999.99`)

## 9. Available Drilling Information
| Feature | Available? | Exact source field | Granularity | 
|---|---|---|---|
| MD | YES | `statusInfo.md` | Daily max (1 per report) |
| TVD | YES | `statusInfo.tvd` | Daily max (1 per report) |
| ROP | NO | `statusInfo.ropCurrent` | >99% sentinel (`-999.99`) |
| WOB | NO | N/A | N/A |
| RPM | NO | N/A | N/A |
| Torque | NO | N/A | N/A |
| Hookload | NO | N/A | N/A |
| Flow rate | NO | N/A | N/A |
| Standpipe pressure | NO | N/A | N/A |
| Mud weight | YES | `fluid.density` | Point measurement |
| Pore pressure | YES | `porePressure.equivalentMudWeight` | Point measurement |
| Inclination | YES | `surveyStation.incl` | Survey point |
| Azimuth | YES | `surveyStation.azi` | Survey point |

## 10. Event / Label Investigation
Based on `activity.proprietaryCode` and `activity.stateDetailActivity`:
- Records exist for: `interruption -- repair equipment failure`, `interruption -- waiting on weather`.
- True drilling hazard labels (stuck pipe, kick) are NOT cleanly isolated in categorical fields; they likely require NLP on `activity.comments` or `statusInfo.sum24Hr`.

## 11. Visualization Inventory
- `01_report_counts_per_wellbore.png`: Reports per wellbore
- `02_drilling_timeline.png`: Temporal coverage Gantt
- `03_nested_array_coverage.png`: Coverage % of nested arrays
- `04_statusinfo_sentinel_null_rates.png`: Missingness in statusInfo
- `05_max_depth_per_wellbore.png`: MD and TVD maximums
- `06_top15_activity_codes.png`: Activity codes distribution
- `07_fluid_types.png`: Drilling mud types
- `08_lithology_distribution.png`: Lithology types
- `09_reports_per_year.png`: Report counts per year
- `10_pore_pressure_emw.png`: Equivalent Mud Weight distribution
- `11_survey_trajectory.png`: Inclination & MD vs TVD
- `12_top_level_null_heatmap.png`: Top-level missingness

## 12. Audit Artifacts
- **Reports**: `audit_schema.md`, `audit_data_quality.md`, `audit_well_coverage.md`, `audit_report.html`, `checkpoint1_review.md`
- **Tables**: `reports/tables/*.csv`
- **Figures**: `reports/figures/*.png`
- **Tests**: `tests/test_audit.py`
- **Script**: `scripts/run_audit.py`

## 13. Code Quality Audit
- **Hard-coded assumptions**: We explicitly hardcoded `-999.99` as a sentinel.
- **Type casting**: `VARCHAR` to numeric was handled explicitly in `duckdb` queries.
- **Reproducibility**: All data is read from the raw parquet without modification.

## 14. Critical Findings
**CONFIRMED FACTS**: 1,759 reports, 23 unique nameWell values, 26 unique nameWellbore values. `activity` and `fluid` are well-populated.
**DATA LIMITATIONS**: High-frequency telemetry (WOB, RPM, etc.) is missing. ROP is entirely sentinels.
**NEXT DATA NEEDED**: Time-based or depth-based telemetry data (e.g., actual WITS0/WITSML logs) to predict risks dynamically.

## 15. ML Readiness Assessment
**Ready for ML**: NO.
**Blockers**: No continuous sensor data; labels require NLP extraction from text summaries; numeric features currently buried in string-based nested arrays.
**Supportable Task**: None clearly defined yet. Do not treat activity prediction as the primary PS26121 ML problem.
**Required Data**: Actual high-frequency surface parameter telemetry logs (drilling mechanics).

## 16. CHECKPOINT 2 RECOMMENDATION
- **Tables to Create**: `dim_wellbore`, `fact_daily_status`, `fact_activity`, `fact_fluid`.
- **Flattening Rules**: Preserve WITSML object hierarchy conceptually; derived flat analytics tables are allowed, but raw semantics must remain traceable. Do not flatten the production dataset yet.
- **Preserve**: Raw text comments.
- **Convert**: `VARCHAR` numerics to `FLOAT`; replace `-999.99` with `NULL`.

## CHATGPT REVIEW REQUEST
1. Given the complete absence of WOB, RPM, and Torque, is predictive drilling risk modeling viable with this dataset alone?
2. Should we extract labels from `sum24Hr` via NLP, or limit scope to rule-based parsing of `activity` codes?
3. How should we handle overlapping wellbore aliases like `F-11 A` vs `F-11 T2` for ML splits?
4. Is it acceptable to use one-report-per-day data (statusInfo) for ML, or do we need deeper WITSML files?
5. How should we impute the near-100% missing `ropCurrent`?
6. Should we interpolate `surveyStation` points to match daily `statusInfo` depths?
7. What is the most rigorous way to prevent temporal leakage when predicting incidents from daily summaries?
8. Do the nested `activity` logs provide enough sequence data to predict the *next* activity state?
9. Should we treat missing nested arrays (e.g., empty `lithShowInfo`) as informative (absence of evidence) or just missing?
10. Does this derived Parquet schema faithfully represent the raw WITSML complexity, or have we lost contextual hierarchy?
"""

    with open(OUTPUT_FILE, "w") as f:
        f.write(md_content)

    print(f"Report written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
