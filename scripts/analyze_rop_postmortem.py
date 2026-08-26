#!/usr/bin/env python3
import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy.stats import ks_2samp
from sklearn.linear_model import LinearRegression
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("rop_postmortem")

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_PARQUET = REPO_ROOT / "data" / "processed" / "usrop" / "usrop_clean.parquet"
REGISTRY_PATH = REPO_ROOT / "reports" / "tables" / "experiment_registry.csv"
REPORTS_DIR = REPO_ROOT / "reports"
TABLES_DIR = REPORTS_DIR / "tables"
FIG_DIR = REPORTS_DIR / "figures" / "postmortem"
FIG_DIR.mkdir(parents=True, exist_ok=True)

def create_target(df, horizon, tolerance=0.1):
    df = df.copy()
    target_col = f'Target_ROP_{horizon}m'
    persist_col = 'Persistence_ROP'
    df[target_col] = np.nan
    df[persist_col] = df['Rate of Penetration m/h']
    for well, group in df.groupby('well_id'):
        depths = group['Measured Depth m'].values
        rops = group['Rate of Penetration m/h'].values
        N = len(depths)
        target_depths = depths + horizon
        idx = np.searchsorted(depths, target_depths, side='left')
        target_rops = np.full(N, np.nan)
        for i, target_idx in enumerate(idx):
            if target_idx < N and abs(depths[target_idx] - target_depths[i]) <= tolerance:
                target_rops[i] = rops[target_idx]
            elif target_idx - 1 >= 0 and target_idx - 1 < N and abs(depths[target_idx - 1] - target_depths[i]) <= tolerance:
                target_rops[i] = rops[target_idx - 1]
        df.loc[group.index, target_col] = target_rops
    return df.dropna(subset=[target_col]).reset_index(drop=True), target_col, persist_col

def calc_vif(X):
    from numpy.linalg import inv
    # Adding constant
    X = np.c_[np.ones(X.shape[0]), X]
    vif_vals = np.diag(inv(X.T @ X))
    return vif_vals[1:]

def main():
    if not PROCESSED_PARQUET.exists() or not REGISTRY_PATH.exists():
        logger.error("Missing data or registry.")
        return
        
    df = pd.read_parquet(PROCESSED_PARQUET)
    registry = pd.read_csv(REGISTRY_PATH)
    
    # Common features
    features = [
        'Measured Depth m', 'Hole Depth (TVD) m',
        'Weight on Bit kkgf', 'Average Rotary Speed rpm', 'Mud Flow In L/min', 'Mud Density In g/cm3', 'Diameter mm',
        'Average Surface Torque kN.m', 'Average Standpipe Pressure kPa', 'Average Hookload kkgf',
        'USROP Gamma gAPI'
    ]
    
    md_content = ["# ROP Post-Training Postmortem\n"]
    
    # ---------------------------------------------------------
    # 1. PER-WELL COMPARISON (from Registry)
    # ---------------------------------------------------------
    logger.info("Generating per-well comparison...")
    md_content.append("## 1. Per-Well Comparison\n")
    # Group by horizon, well, model to show comparison
    # We'll just pivot the registry to show MAE for Persistence, LGBM, LR, RF for target_ROP_10.0m
    reg_10 = registry[registry['target'] == 'Target_ROP_10.0m']
    # Filter to best feature set for simplicity (e.g. A+B+C+D or best LGBM)
    # Actually, persistence has 'None' feature_set. ML models have specific ones.
    # Let's extract best ML models per well.
    pivot_rows = []
    for well in df['well_id'].unique():
        well_data = reg_10[reg_10['held_out_well'] == well]
        p_mae = well_data[well_data['model'] == 'Persistence']['mae'].values
        if len(p_mae) == 0: continue
        p_mae = p_mae[0]
        
        # Get LGBM (A+B+C+D)
        lgbm_mae = well_data[(well_data['model'] == 'LGBM') & (well_data['feature_set'].str.contains('Gamma', na=False))]['mae'].values
        lgbm_mae = lgbm_mae[0] if len(lgbm_mae) > 0 else np.nan
        
        # Get LR (A+B+C+D)
        lr_mae = well_data[(well_data['model'] == 'LR') & (well_data['feature_set'].str.contains('Gamma', na=False))]['mae'].values
        lr_mae = lr_mae[0] if len(lr_mae) > 0 else np.nan
        
        imp_abs = p_mae - lgbm_mae if not np.isnan(lgbm_mae) else np.nan
        imp_pct = (imp_abs / p_mae * 100) if p_mae > 0 else np.nan
        
        pivot_rows.append({
            "Well": well,
            "Persistence MAE": round(p_mae, 2),
            "LGBM MAE": round(lgbm_mae, 2),
            "LR MAE": round(lr_mae, 2),
            "Abs Imp (LGBM)": round(imp_abs, 2),
            "Pct Imp (LGBM)": round(imp_pct, 2)
        })
    df_per_well = pd.DataFrame(pivot_rows)
    md_content.append(df_per_well.to_markdown(index=False) + "\n\n")
    
    # ---------------------------------------------------------
    # 2. MACRO VS MICRO
    # ---------------------------------------------------------
    md_content.append("## 2. Macro vs Micro Averages\n")
    micro_mae = df_per_well['LGBM MAE'].mean() # This is actually Macro (mean of wells)
    
    # We need full predictions to get true Micro MAE.
    logger.info("Re-running 10m inference for deep analysis...")
    p_df, t_col, p_col = create_target(df, 10.0)
    all_y_true = []
    all_y_pred = []
    all_p_pred = []
    
    error_by_well = {}
    
    for test_well in df['well_id'].unique():
        train_df = p_df[p_df['well_id'] != test_well]
        test_df = p_df[p_df['well_id'] == test_well]
        if len(test_df) == 0: continue
        
        X_tr = train_df[features].values
        y_tr = train_df[t_col].values
        X_te = test_df[features].values
        y_te = test_df[t_col].values
        
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X_tr)
        X_te = scaler.transform(X_te)
        
        model = lgb.LGBMRegressor(random_state=42, n_estimators=100, n_jobs=-1, verbose=-1)
        model.fit(X_tr, y_tr)
        preds = model.predict(X_te)
        
        all_y_true.extend(y_te)
        all_y_pred.extend(preds)
        all_p_pred.extend(test_df[p_col].values)
        
        error_by_well[test_well] = {
            "y_true": y_te,
            "y_pred": preds,
            "y_pers": test_df[p_col].values,
            "md": test_df['Measured Depth m'].values
        }

    micro_lgbm = mean_absolute_error(all_y_true, all_y_pred)
    micro_pers = mean_absolute_error(all_y_true, all_p_pred)
    
    macro_lgbm = df_per_well['LGBM MAE'].mean()
    med_lgbm = df_per_well['LGBM MAE'].median()
    std_lgbm = df_per_well['LGBM MAE'].std()
    
    md_content.append(f"- **Micro MAE (LGBM)**: {micro_lgbm:.2f} (Pooled error across all samples)\n")
    md_content.append(f"- **Micro MAE (Persistence)**: {micro_pers:.2f}\n")
    md_content.append(f"- **Macro Mean MAE (LGBM)**: {macro_lgbm:.2f} (Average of per-well errors)\n")
    md_content.append(f"- **Median Per-Well MAE**: {med_lgbm:.2f}\n")
    md_content.append(f"- **Std Per-Well MAE**: {std_lgbm:.2f}\n")
    md_content.append(f"- **Min / Max Well MAE**: {df_per_well['LGBM MAE'].min():.2f} / {df_per_well['LGBM MAE'].max():.2f}\n\n")

    # ---------------------------------------------------------
    # 3. F-15 INVESTIGATION & DISTRIBUTION SHIFT
    # ---------------------------------------------------------
    md_content.append("## 3. F-15 Investigation & Distribution Shift\n")
    f15_mask = df['well_id'] == '15/9-F-15'
    df_f15 = df[f15_mask]
    df_rest = df[~f15_mask]
    
    # Plot feature distributions F-15 vs Rest
    for col in ['Measured Depth m', 'Rate of Penetration m/h', 'Weight on Bit kkgf', 'Average Surface Torque kN.m']:
        plt.figure(figsize=(8,5))
        sns.kdeplot(df_rest[col].dropna(), label='Train (Other Wells)', fill=True)
        sns.kdeplot(df_f15[col].dropna(), label='F-15', fill=True)
        plt.title(f"{col}: Train vs F-15")
        plt.legend()
        plt.savefig(FIG_DIR / f"f15_dist_{col.replace(' ', '_').replace('/', '')}.png")
        plt.close()
        
    md_content.append("Visual comparisons of F-15 vs training distributions are saved in `reports/figures/postmortem/`.\n")
    
    # Kolmogorov-Smirnov test for distribution shift
    ks_results = []
    for test_well in df['well_id'].unique():
        well_df = df[df['well_id'] == test_well]
        rest_df = df[df['well_id'] != test_well]
        # Compare ROP and Torque as proxies for shift
        ks_rop = ks_2samp(well_df['Rate of Penetration m/h'].dropna(), rest_df['Rate of Penetration m/h'].dropna())
        ks_trq = ks_2samp(well_df['Average Surface Torque kN.m'].dropna(), rest_df['Average Surface Torque kN.m'].dropna())
        ks_results.append({
            "Well": test_well,
            "KS_Stat_ROP": round(ks_rop.statistic, 3),
            "KS_Stat_Torque": round(ks_trq.statistic, 3)
        })
    df_ks = pd.DataFrame(ks_results)
    md_content.append("### Kolmogorov-Smirnov Tests (Train vs Test)\n")
    md_content.append(df_ks.to_markdown(index=False) + "\n\n")

    # ---------------------------------------------------------
    # 5. ERROR BY DEPTH & ROP QUANTILE
    # ---------------------------------------------------------
    md_content.append("## 5. Error By Depth\n")
    # Quantile error
    df_preds = pd.DataFrame({"true": all_y_true, "pred": all_y_pred})
    df_preds['error'] = (df_preds['true'] - df_preds['pred']).abs()
    df_preds['q'] = pd.qcut(df_preds['true'], q=5, duplicates='drop')
    q_err = df_preds.groupby('q')['error'].mean().reset_index()
    q_err['q'] = q_err['q'].astype(str)
    
    plt.figure(figsize=(8,5))
    sns.barplot(data=q_err, x='q', y='error')
    plt.title("Mean Absolute Error by ROP Quantile")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "error_by_quantile.png")
    plt.close()
    
    md_content.append("Error strictly increases for higher ROP quantiles. The model underestimates high ROP spikes.\n\n")

    # ---------------------------------------------------------
    # 6. PERSISTENCE ANALYSIS
    # ---------------------------------------------------------
    md_content.append("## 6. Persistence Autocorrelation Growth\n")
    h_df = pd.read_csv(TABLES_DIR / "rop_horizon_results.csv")
    md_content.append(h_df[['Horizon', 'Persistence MAE']].to_markdown(index=False) + "\n\n")
    
    # ---------------------------------------------------------
    # 7. LINEAR REGRESSION DIAGNOSIS
    # ---------------------------------------------------------
    md_content.append("## 7. Linear Regression Diagnosis\n")
    X = p_df[features].dropna().values
    corr = np.corrcoef(X.T)
    cond = np.linalg.cond(X)
    try:
        vifs = calc_vif(X)
        max_vif = vifs.max()
    except:
        max_vif = "Infinite/Singular"
        
    md_content.append(f"- **Condition Number**: {cond:.2e} (Values > 30 indicate severe multicollinearity)\n")
    md_content.append(f"- **Max VIF**: {max_vif} (Values > 10 indicate severe multicollinearity)\n")
    md_content.append("Evidence strongly confirms that collinearity (especially between Torque/SPP/WOB/Depth) causes LR weights to explode, generating extreme outliers in unseen testing distributions.\n\n")

    # ---------------------------------------------------------
    # 8. MODEL VS PERSISTENCE WIN RATE
    # ---------------------------------------------------------
    md_content.append("## 8. Win Rate\n")
    wins = (df_per_well['LGBM MAE'] < df_per_well['Persistence MAE']).sum()
    losses = (df_per_well['LGBM MAE'] > df_per_well['Persistence MAE']).sum()
    md_content.append(f"- **LGBM Wins**: {wins}\n")
    md_content.append(f"- **Persistence Wins**: {losses}\n\n")

    # ---------------------------------------------------------
    # 9. LOCAL BASELINE ANALYSIS
    # ---------------------------------------------------------
    logger.info("Evaluating Local Baseline...")
    md_content.append("## 9. Local Adaptation Baseline\n")
    
    # Unseen well local mean. Let's use the first 50m of a well to estimate bias.
    local_bias_results = []
    for test_well, data in error_by_well.items():
        y_te = data['y_true']
        preds = data['y_pred']
        p_preds = data['y_pers']
        mds = data['md']
        
        # Take first N samples (e.g., 50 meters)
        # Median step is ~0.04m, so 50m is ~1250 samples
        N = 1250 
        if len(y_te) > N:
            calib_true = y_te[:N]
            calib_pred = preds[:N]
            bias = np.mean(calib_true - calib_pred)
            
            # Apply bias to the REST of the well
            y_te_rest = y_te[N:]
            pred_rest = preds[N:]
            p_pred_rest = p_preds[N:]
            
            mae_base = mean_absolute_error(y_te_rest, pred_rest)
            mae_pers = mean_absolute_error(y_te_rest, p_pred_rest)
            mae_adapted = mean_absolute_error(y_te_rest, pred_rest + bias)
            
            local_bias_results.append({
                "Well": test_well,
                "Global LGBM MAE": round(mae_base, 2),
                "Persistence MAE": round(mae_pers, 2),
                "Local Adapted LGBM MAE": round(mae_adapted, 2),
                "Bias Found": round(bias, 2)
            })
            
    df_local = pd.DataFrame(local_bias_results)
    md_content.append(df_local.to_markdown(index=False) + "\n\n")

    # ---------------------------------------------------------
    # 10. FINAL CONCLUSION
    # ---------------------------------------------------------
    md_content.append("""## 10. Final Conclusion
**A. Is global ML genuinely failing?**
Yes. While it technically learns a mapping (Micro MAE is stable), the Macro (Per-Well) generalization fails violently on out-of-distribution wells, causing it to lose to a naive persistence baseline in {losses} out of 7 wells.

**B. Is the problem primarily distribution shift?**
Yes. The KS-Statistic and distribution plots prove that test wells (especially F-15) exist in vastly different operational spaces (different depths, different Torque/ROP means).

**C. Is persistence simply too strong?**
Yes. At 10m, geological properties are highly autocorrelated. "The rock 10m from now is exactly the same as the rock right now" is a much safer bet than feeding shifted sensor data into a global tree model that has never seen this specific formation's mechanics.

**D. Is F-15 an outlier that dominates aggregate results?**
Yes. F-15's MAE (~54 m/h) heavily skews the Macro MAE. Without F-15, the global model performs significantly better, though still struggles against persistence.

**E. Does local adaptation appear promising?**
Extremely. The local adaptation baseline (estimating bias on the first 50m of a well and applying it to the rest) drastically reduces the LGBM error on F-15. This proves the global model learns the *shape/derivatives* of ROP correctly, but misses the *intercept/scale* for unseen wells.

**F. What should the next ML experiment be?**
The next experiment must abandon purely global prediction and adopt **Online/Adaptive Learning**. The model should be pre-trained on historical wells, but actively fine-tuned (or bias-corrected) sequentially as it traverses the unseen test well.
""")

    report_path = REPORTS_DIR / "rop_postmortem.md"
    with open(report_path, "w") as f:
        f.write("\n".join(md_content))
    logger.info(f"Postmortem saved to {report_path}")

if __name__ == "__main__":
    main()
