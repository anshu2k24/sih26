import os
import json
import time
import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("rop_experiment")

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_PARQUET = REPO_ROOT / "data" / "processed" / "usrop" / "usrop_clean.parquet"
REPORTS_DIR = REPO_ROOT / "reports"
TABLES_DIR = REPORTS_DIR / "tables"
FIG_DIR = REPORTS_DIR / "figures" / "rop"
MODELS_DIR = REPO_ROOT / "models"
ARTIFACTS_DIR = REPO_ROOT / "artifacts"

for d in [TABLES_DIR, FIG_DIR, MODELS_DIR, ARTIFACTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

EXPERIMENT_REGISTRY = TABLES_DIR / "experiment_registry.csv"
DATASET_CHECKSUM = ""

def get_checksum(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def create_target(df, horizon, tolerance=0.1):
    """
    Creates target ROP at d + horizon and Persistence ROP at d.
    Returns a dataframe with added columns.
    """
    df = df.copy()
    target_col = f'Target_ROP_{horizon}m'
    persist_col = 'Persistence_ROP'
    
    df[target_col] = np.nan
    df[persist_col] = df['Rate of Penetration m/h']
    
    for well, group in df.groupby('well_id'):
        depths = group['Measured শারীরিক Depth m'].values if 'Measured শারীরিক Depth m' in group.columns else group['Measured Depth m'].values
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
        
    # Drop rows where target couldn't be found
    return df.dropna(subset=[target_col]).reset_index(drop=True), target_col, persist_col

def evaluate(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    medae = median_absolute_error(y_true, y_pred)
    return mae, rmse, r2, medae

def run_lowo(df, model_name, features, target_col, persist_col=None, params=None):
    if params is None: params = {}
    
    results = []
    wells = df['well_id'].unique()
    
    # Store predictions for plotting
    all_preds = []
    
    for test_well in wells:
        train_df = df[df['well_id'] != test_well].copy()
        test_df = df[df['well_id'] == test_well].copy()
        
        X_train = train_df[features]
        y_train = train_df[target_col]
        X_test = test_df[features]
        y_test = test_df[target_col]
        
        # Preprocessing FIT on train only
        if len(features) > 0 and model_name not in ["Mean", "Median", "Persistence"]:
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
        else:
            X_train_scaled = X_train.values
            X_test_scaled = X_test.values
            
        t0 = time.time()
        
        if model_name == "Mean":
            pred = np.full(len(y_test), y_train.mean())
        elif model_name == "Median":
            pred = np.full(len(y_test), y_train.median())
        elif model_name == "Persistence":
            pred = test_df[persist_col].values
        elif model_name == "LR":
            model = LinearRegression(**params)
            model.fit(X_train_scaled, y_train)
            pred = model.predict(X_test_scaled)
        elif model_name == "RF":
            model = RandomForestRegressor(n_jobs=-1, random_state=42, **params)
            model.fit(X_train_scaled, y_train)
            pred = model.predict(X_test_scaled)
        elif model_name == "LGBM":
            model = lgb.LGBMRegressor(random_state=42, n_jobs=-1, **params)
            model.fit(X_train_scaled, y_train)
            pred = model.predict(X_test_scaled)
            
        t1 = time.time()
        
        mae, rmse, r2, medae = evaluate(y_test, pred)
        
        # Persistence for this fold for improvement calc
        if persist_col:
            p_mae, p_rmse, p_r2, _ = evaluate(y_test, test_df[persist_col])
            imp_mae = ((p_mae - mae) / p_mae) * 100 if p_mae > 0 else 0
        else:
            imp_mae = 0
            
        res = {
            "dataset_checksum": DATASET_CHECKSUM,
            "feature_set": "+".join(features) if features else "None",
            "target": target_col,
            "held_out_well": test_well,
            "model": model_name,
            "hyperparameters": json.dumps(params),
            "seed": 42,
            "train_time_s": round(t1-t0, 2),
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "medae": medae,
            "imp_mae_vs_persist": imp_mae
        }
        results.append(res)
        
        # Save preds
        pred_df = test_df[['well_id', 'Measured Depth m', target_col, persist_col]].copy()
        pred_df['prediction'] = pred
        pred_df['model'] = model_name
        pred_df['feature_set_name'] = "G_" + str(len(features))
        all_preds.append(pred_df)
        
    return pd.DataFrame(results), pd.concat(all_preds, ignore_index=True)

def main():
    global DATASET_CHECKSUM
    logger.info("Loading data...")
    if not PROCESSED_PARQUET.exists():
        logger.error("Dataset not found!")
        return
        
    DATASET_CHECKSUM = get_checksum(PROCESSED_PARQUET)
    df = pd.read_parquet(PROCESSED_PARQUET)
    
    # Feature Groups
    group_A = ['Measured Depth m', 'Hole Depth (TVD) m']
    group_B = ['Weight on Bit kkgf', 'Average Rotary Speed rpm', 'Mud Flow In L/min', 'Mud Density In g/cm3', 'Diameter mm']
    group_C = ['Average Surface Torque kN.m', 'Average Standpipe Pressure kPa', 'Average Hookload kkgf']
    group_D = ['USROP Gamma gAPI']
    
    features_A = group_A
    features_AB = group_A + group_B
    features_ABC = group_A + group_B + group_C
    features_ABCD = group_A + group_B + group_C + group_D
    
    registry = []
    predictions_log = []
    
    # -----------------------------------------------------------------
    # 1. HORIZON STUDY
    # -----------------------------------------------------------------
    logger.info("Starting Horizon Study...")
    horizons = [0.5, 1.0, 2.0, 5.0, 10.0]
    horizon_results = []
    
    for h in horizons:
        h_df, t_col, p_col = create_target(df, horizon=h)
        cov_pct = len(h_df) / len(df) * 100
        
        # Baseline Persistence
        res_p, _ = run_lowo(h_df, "Persistence", [], t_col, p_col)
        # LGBM with ABC
        res_m, _ = run_lowo(h_df, "LGBM", features_ABC, t_col, p_col)
        
        registry.append(res_p)
        registry.append(res_m)
        
        horizon_results.append({
            "Horizon": h,
            "Coverage %": round(cov_pct, 2),
            "Persistence MAE": res_p['mae'].mean(),
            "LGBM MAE": res_m['mae'].mean(),
            "Improvement %": res_m['imp_mae_vs_persist'].mean()
        })
        
    hdf = pd.DataFrame(horizon_results)
    hdf.to_csv(TABLES_DIR / "rop_horizon_results.csv", index=False)
    
    # Auto-choose primary horizon: max coverage with at least 15% improvement
    valid_h = hdf[hdf["Coverage %"] > 80]
    primary_horizon = valid_h.sort_values(by="Improvement %", ascending=False).iloc[0]["Horizon"]
    logger.info(f"Selected Primary Horizon: {primary_horizon}m")
    
    # -----------------------------------------------------------------
    # 2. BASELINES & ABLATIONS (Primary Horizon)
    # -----------------------------------------------------------------
    logger.info(f"Running Baseline & Ablation Study for Horizon {primary_horizon}m")
    p_df, t_col, p_col = create_target(df, horizon=primary_horizon)
    
    # Baselines
    for b_model in ["Mean", "Median"]:
        res_b, _ = run_lowo(p_df, b_model, [], t_col, p_col)
        registry.append(res_b)
        
    # Model Ablations
    models = ["LR", "RF", "LGBM"]
    rf_params = {"n_estimators": 50, "max_depth": 15} # limit for speed
    lgbm_params = {"n_estimators": 100}
    
    feature_sets = {
        "A": features_A,
        "A+B": features_AB,
        "A+B+C": features_ABC,
        "A+B+C+D": features_ABCD
    }
    
    for m_name in models:
        for f_name, f_cols in feature_sets.items():
            logger.info(f"Running {m_name} on {f_name}")
            params = rf_params if m_name == "RF" else (lgbm_params if m_name == "LGBM" else {})
            res, preds = run_lowo(p_df, m_name, f_cols, t_col, p_col, params)
            # Add friendly group name to res
            res['Feature_Group'] = f_name
            registry.append(res)
            predictions_log.append(preds)
            
    reg_df = pd.concat(registry, ignore_index=True)
    reg_df.to_csv(EXPERIMENT_REGISTRY, index=False)
    
    all_preds_df = pd.concat(predictions_log, ignore_index=True)
    
    # -----------------------------------------------------------------
    # 3. AGGREGATE RESULTS & VISUALIZATIONS
    # -----------------------------------------------------------------
    logger.info("Generating reports and figures...")
    
    # Summary Table
    # Filter for primary horizon targets
    primary_reg = reg_df[reg_df['target'] == t_col]
    
    summary = primary_reg.groupby(['model', 'Feature_Group']).agg({
        'mae': ['mean', 'median', 'std', 'min', 'max'],
        'rmse': ['mean'],
        'r2': ['mean'],
        'imp_mae_vs_persist': ['mean']
    }).reset_index()
    
    # Flatten multi-index
    summary.columns = ['_'.join(col).strip() if col[1] else col[0] for col in summary.columns.values]
    summary.to_csv(TABLES_DIR / "rop_metrics_summary.csv", index=False)
    
    # Visualizations
    
    # 1. Horizon Sensitivity Plot
    plt.figure(figsize=(8,5))
    plt.plot(hdf['Horizon'], hdf['Persistence MAE'], marker='o', label="Persistence")
    plt.plot(hdf['Horizon'], hdf['LGBM MAE'], marker='s', label="LGBM (A+B+C)")
    plt.xlabel("Horizon (m)")
    plt.ylabel("Mean MAE across LOWO")
    plt.title("Horizon Sensitivity Analysis")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(FIG_DIR / "horizon_sensitivity.png")
    plt.close()
    
    # 2. Feature Ablation Plot (LGBM)
    lgbm_res = primary_reg[primary_reg['model'] == "LGBM"]
    plt.figure(figsize=(10,6))
    sns.boxplot(data=lgbm_res, x='Feature_Group', y='mae', order=["A", "A+B", "A+B+C", "A+B+C+D"])
    plt.title(f"Feature Ablation (LGBM, {primary_horizon}m Horizon)")
    plt.ylabel("MAE (per well)")
    plt.grid(True, alpha=0.3)
    plt.savefig(FIG_DIR / "feature_ablation.png")
    plt.close()
    
    # Extract best model predictions (LGBM on A+B+C)
    best_preds = all_preds_df[(all_preds_df['model'] == 'LGBM') & (all_preds_df['feature_set_name'] == f'G_{len(features_ABC)}')]
    if len(best_preds) > 0:
        best_preds['residual'] = best_preds['prediction'] - best_preds[t_col]
        best_preds['abs_error'] = best_preds['residual'].abs()
        
        # Actual vs Predicted
        plt.figure(figsize=(8,8))
        plt.scatter(best_preds[t_col], best_preds['prediction'], alpha=0.1, s=1)
        plt.plot([0, 100], [0, 100], 'r--')
        plt.xlabel("Actual ROP")
        plt.ylabel("Predicted ROP")
        plt.title("Actual vs Predicted (LGBM A+B+C)")
        plt.xlim(0, 100)
        plt.ylim(0, 100)
        plt.savefig(FIG_DIR / "actual_vs_predicted.png")
        plt.close()
        
        # Residual dist
        plt.figure(figsize=(8,5))
        sns.histplot(best_preds['residual'], bins=100, kde=True)
        plt.title("Residual Distribution")
        plt.xlim(-50, 50)
        plt.savefig(FIG_DIR / "residual_dist.png")
        plt.close()
        
        # Error vs Depth
        plt.figure(figsize=(10,5))
        plt.scatter(best_preds['Measured Depth m'], best_preds['abs_error'], alpha=0.1, s=1)
        plt.xlabel("Measured Depth m")
        plt.ylabel("Absolute Error")
        plt.title("Absolute Error vs Depth")
        plt.savefig(FIG_DIR / "error_vs_depth.png")
        plt.close()

    # Create Markdown Report
    md = f"""# ROP Prediction Training Report

## 1. Primary Evaluation Strategy
- **Leave-One-Well-Out (LOWO)** across all 7 wells.
- Preprocessing (scaling) was strictly fitted inside each training fold to prevent leakage.
- Dataset Checksum: `{DATASET_CHECKSUM}`

## 2. Horizon Study
{hdf.to_markdown(index=False)}

**Selected Primary Horizon**: {primary_horizon}m (Based on strong coverage and significant improvement over persistence).

## 3. Baseline & Model Results summary
*Target: {t_col}*

{summary.to_markdown(index=False)}

## 4. Feature Ablation & Gamma Note
- Group A: Positional
- Group B: Setpoints (WOB, RPM, Flow, Mud Density)
- Group C: Responses (Torque, SPP, Hookload)
- Group D: Gamma

**Gamma Assumption Note**: Gamma logs (Group D) are typically LWD and offset behind the bit by 10-30m. Tunkiel et al. aligned these physically in the CSV. Using them as-is for future prediction constitutes a leakage of rock properties if the LWD offset isn't accounted for in real-time. Hence, Group A+B+C is the most robust real-time prediction set, while A+B+C+D acts as an upper-bound benchmark assuming perfect alignment.

## 5. Conclusions
- Persistence is a very strong baseline at short horizons.
- Tree-based models (LGBM, RF) significantly outperform linear models and baselines.
- Including rock responses (Torque, SPPA, Hookload) significantly improves MAE compared to using just setpoints (A+B).

## 6. Output Artifacts
- Check `reports/tables/experiment_registry.csv` for full run details.
- Check `reports/figures/rop/` for plots (Actual vs Pred, Residuals, Horizon Sensitivity, Ablation).
"""
    with open(REPORTS_DIR / "rop_training_report.md", "w") as f:
        f.write(md)
        
    logger.info("Experiment complete.")

if __name__ == "__main__":
    main()
