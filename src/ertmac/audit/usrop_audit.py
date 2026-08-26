import os
import re
import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging

# Ensure output paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "usrop"
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "usrop"
REPORTS_DIR = REPO_ROOT / "reports"
TABLES_DIR = REPORTS_DIR / "tables"
FIG_DIR = REPORTS_DIR / "figures" / "usrop"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("usrop_audit")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# File to well mapping
FILE_TO_WELL = {
    "USROP_A 0 N-NA_F-9_Ad.csv": "15/9-F-9 A",
    "USROP_A 1 N-S_F-7d.csv": "15/9-F-7",
    "USROP_A 2 N-SH_F-14d.csv": "15/9-F-14",
    "USROP_A 3 N-SH-F-15d.csv": "15/9-F-15",
    "USROP_A 4 N-SH_F-15Sd.csv": "15/9-F-15S",
    "USROP_A 5 N-SH-F-5d.csv": "15/9-F-5",
    "USROP_A 6 N-SH_F-9d.csv": "15/9-F-9"
}

def get_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def plot_distributions(df, cols, fig_prefix):
    for col in cols:
        plt.figure(figsize=(10, 5))
        sns.histplot(df[col].dropna(), kde=True, bins=50)
        plt.title(f"Distribution of {col}")
        plt.xlabel(col)
        plt.ylabel("Count")
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', col)
        plt.tight_layout()
        plt.savefig(FIG_DIR / f"{fig_prefix}_{safe_name}_distribution.png", dpi=150)
        plt.close()

def run_audit():
    logger.info("Starting USROP Audit...")
    
    # 1. RAW DATA VALIDATION & WELL IDENTITY
    all_dfs = []
    schema_stats = []
    
    for file, well_id in FILE_TO_WELL.items():
        filepath = RAW_DIR / file
        if not filepath.exists():
            logger.error(f"Missing {file}")
            continue
            
        sha = get_sha256(filepath)
        df = pd.read_csv(filepath)
        
        # Remove unnamed index artifact
        if "Unnamed: 0" in df.columns:
            df = df.drop(columns=["Unnamed: 0"])
            
        df['well_id'] = well_id
        df['filename'] = file
        df['sha256'] = sha
        all_dfs.append(df)
        
    df_all = pd.concat(all_dfs, ignore_index=True)
    
    logger.info(f"Total Rows: {len(df_all)}")
    assert len(df_all) == 198928, "Total row count mismatch!"
    
    # Sort by well and depth
    df_all = df_all.sort_values(by=['well_id', 'Measured Depth m']).reset_index(drop=True)
    
    # --- PHYSICAL PLAUSIBILITY ---
    rules = {
        "ROP <= 0": df_all['Rate of Penetration m/h'] <= 0,
        "WOB <= 0": df_all['Weight on Bit kkgf'] <= 0,
        "RPM < 0": df_all['Average Rotary Speed rpm'] < 0,
        "Torque < 0": df_all['Average Surface Torque kN.m'] < 0,
        "Flow < 0": df_all['Mud Flow In L/min'] < 0,
        "Mud density <= 0": df_all['Mud Density In g/cm3'] <= 0,
        "Diameter <= 0": df_all['Diameter mm'] <= 0,
        "Hookload < 0": df_all['Average Hookload kkgf'] < 0,
        "TVD <= 0": df_all['Hole Depth (TVD) m'] <= 0,
        "TVD > MD + 0.1": df_all['Hole Depth (TVD) m'] > (df_all['Measured Depth m'] + 0.1)
    }
    
    quality_flags = []
    for rule_name, mask in rules.items():
        count = mask.sum()
        pct = (count / len(df_all)) * 100
        affected_wells = df_all.loc[mask, 'well_id'].unique().tolist()
        quality_flags.append({
            "Rule": rule_name,
            "Violations": count,
            "Percentage": round(pct, 4),
            "Affected Wells": ", ".join(affected_wells)
        })
    pd.DataFrame(quality_flags).to_csv(TABLES_DIR / "usrop_quality_flags.csv", index=False)
    
    # --- DEPTH SAMPLING ---
    df_all['MD_step'] = df_all.groupby('well_id')['Measured Depth m'].diff()
    
    well_summaries = []
    for well, group in df_all.groupby('well_id'):
        steps = group['MD_step'].dropna()
        well_summaries.append({
            "well": well,
            "row_count": len(group),
            "MD_min": group['Measured Depth m'].min(),
            "MD_max": group['Measured Depth m'].max(),
            "depth_span": group['Measured Depth m'].max() - group['Measured Depth m'].min(),
            "median_MD_step": steps.median(),
            "mean_MD_step": steps.mean(),
            "p1_step": steps.quantile(0.01),
            "p50_step": steps.median(),
            "p99_step": steps.quantile(0.99),
            "duplicate_MDs": (steps == 0).sum(),
            "non_monotonic_MDs": (steps < 0).sum(),
            "gaps_gt_1m": (steps > 1).sum()
        })
    df_well_summary = pd.DataFrame(well_summaries)
    df_well_summary.to_csv(TABLES_DIR / "usrop_well_summary.csv", index=False)
    
    # --- EXACT SCHEMA ---
    schema = []
    for col in df_all.columns:
        if col in ['well_id', 'filename', 'sha256', 'MD_step']: continue
        schema.append({
            "field": col,
            "dtype": str(df_all[col].dtype),
            "valid_range": f"[{df_all[col].min():.2f}, {df_all[col].max():.2f}]",
            "missingness": df_all[col].isna().sum()
        })
    pd.DataFrame(schema).to_csv(TABLES_DIR / "usrop_schema.csv", index=False)
    
    # --- EDA PLOTS ---
    # Global distributions
    numeric_cols = [c for c in df_all.columns if df_all[c].dtype in [np.float64, np.int64] and c != 'MD_step']
    plot_distributions(df_all, numeric_cols, "00_global")
    
    # Correlation matrix
    plt.figure(figsize=(12, 10))
    corr = df_all[numeric_cols].corr()
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", square=True)
    plt.title("USROP Correlation Matrix")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "16_correlation_matrix.png", dpi=150)
    plt.close()
    
    # ROP vs MD per well (subsampled for plot)
    plt.figure(figsize=(14, 8))
    for well in df_all['well_id'].unique():
        sub = df_all[df_all['well_id'] == well].iloc[::10] # decimate by 10
        plt.scatter(sub['Measured Depth m'], sub['Rate of Penetration m/h'], s=2, alpha=0.5, label=well)
    plt.title("ROP vs MD (Decimated x10)")
    plt.xlabel("MD [m]")
    plt.ylabel("ROP [m/h]")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "17_rop_vs_md_per_well.png", dpi=150)
    plt.close()

    # MD Coverage per well
    plt.figure(figsize=(10, 6))
    for i, well in enumerate(df_all['well_id'].unique()):
        sub = df_all[df_all['well_id'] == well]
        plt.plot([sub['Measured Depth m'].min(), sub['Measured Depth m'].max()], [i, i], marker='o', lw=3)
    plt.yticks(range(len(df_all['well_id'].unique())), df_all['well_id'].unique())
    plt.title("MD Coverage by Well")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "03_md_coverage.png", dpi=150)
    plt.close()

    # MD step histogram
    plt.figure(figsize=(10, 5))
    sns.histplot(df_all['MD_step'].dropna(), bins=100, binrange=(0, 0.2))
    plt.title("MD Step Distribution")
    plt.savefig(FIG_DIR / "04_md_step_distribution.png", dpi=150)
    plt.close()
    
    # --- PROCESSED EXPORT ---
    # We do NOT do feature engineering. Just save the validated dataset.
    df_all.to_parquet(PROCESSED_DIR / "usrop_clean.parquet", index=False)
    
if __name__ == "__main__":
    run_audit()
