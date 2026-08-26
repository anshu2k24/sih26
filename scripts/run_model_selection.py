#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
import logging
from scipy.stats import linregress

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("model_sel")

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_PARQUET = REPO_ROOT / "data" / "processed" / "usrop" / "usrop_clean.parquet"
REPORTS_DIR = REPO_ROOT / "reports"
TABLES_DIR = REPORTS_DIR / "tables"
FIG_DIR = REPORTS_DIR / "figures" / "model_selection"
for d in [TABLES_DIR, FIG_DIR]: d.mkdir(parents=True, exist_ok=True)

def calc_metrics(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    medae = median_absolute_error(y_true, y_pred)
    return mae, rmse, r2, medae

def compute_rolling_stats(depth, values, window):
    N = len(depth)
    start_idx = np.searchsorted(depth, depth - window, side='left')
    c_val = np.zeros(N+1); c_val[1:] = np.cumsum(values)
    c_val2 = np.zeros(N+1); c_val2[1:] = np.cumsum(values**2)
    counts = np.arange(1, N+1) - start_idx
    counts = np.maximum(counts, 1)
    
    mean_val = (c_val[np.arange(1, N+1)] - c_val[start_idx]) / counts
    var_val = ((c_val2[np.arange(1, N+1)] - c_val2[start_idx]) / counts) - mean_val**2
    std_val = np.sqrt(np.maximum(var_val, 0))
    delta_val = values - values[start_idx]
    return mean_val, std_val, delta_val

def compute_ema(rops, halflife_samples=50):
    return pd.Series(rops).ewm(halflife=halflife_samples).mean().values

def create_target(df, horizon, tolerance=0.1):
    df = df.copy()
    target_col = f'Target_{horizon}m'
    persist_col = f'Persist_{horizon}m'
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

def main():
    if not PROCESSED_PARQUET.exists(): return
    df = pd.read_parquet(PROCESSED_PARQUET)
    
    logger.info("Computing EMA baseline...")
    ema_vals = []
    for well, group in df.groupby('well_id'):
        ema_vals.extend(compute_ema(group['Rate of Penetration m/h'].values))
    df['EMA_2m'] = ema_vals
    
    logger.info("Generating target...")
    df, t_col, p_col = create_target(df, 10.0)
    
    logger.info("Engineering ROP features for Static LGBM...")
    w_list = [0.5, 1.0, 2.0, 5.0, 10.0]
    f_rop_hist = []
    
    new_cols = {}
    for well, group in df.groupby('well_id'):
        depths = group['Measured Depth m'].values
        rops = group['Rate of Penetration m/h'].values
        for w in w_list:
            m_v, s_v, d_v = compute_rolling_stats(depths, rops, w)
            new_cols[f"ROP_m_{w}"] = new_cols.get(f"ROP_m_{w}", []) + list(m_v)
            new_cols[f"ROP_s_{w}"] = new_cols.get(f"ROP_s_{w}", []) + list(s_v)
            new_cols[f"ROP_d_{w}"] = new_cols.get(f"ROP_d_{w}", []) + list(d_v)
            for fn in [f"ROP_m_{w}", f"ROP_s_{w}", f"ROP_d_{w}"]:
                if fn not in f_rop_hist: f_rop_hist.append(fn)
                
    for k,v in new_cols.items(): df[k] = v
    
    logger.info("Training Static LGBM (LOWO)...")
    df['LGBM'] = np.nan
    for test_well in df['well_id'].unique():
        tr = df[df['well_id'] != test_well]
        te = df[df['well_id'] == test_well]
        sc = StandardScaler()
        X_tr = sc.fit_transform(tr[f_rop_hist].values)
        y_tr = tr[t_col].values
        X_te = sc.transform(te[f_rop_hist].values)
        model = lgb.LGBMRegressor(random_state=42, n_estimators=100, n_jobs=-1, verbose=-1)
        model.fit(X_tr, y_tr)
        df.loc[te.index, 'LGBM'] = model.predict(X_te)
        
    # Candidates
    candidates = [p_col, 'EMA_2m', 'LGBM']
    cand_names = ['Persistence', 'EMA', 'LGBM']
    
    logger.info("Extracting Warm-up Statistics and Errors...")
    warmups = [25.0, 50.0, 100.0, 200.0]
    wells = df['well_id'].unique()
    
    # We will build a dataframe of stats per well per warmup
    stats_list = []
    
    for wu in warmups:
        for well in wells:
            group = df[df['well_id'] == well].copy()
            depths = group['Measured Depth m'].values
            if len(depths) == 0: continue
            
            start_d = depths[0]
            wu_mask = depths <= start_d + wu
            te_mask = depths > start_d + wu
            
            wu_group = group[wu_mask]
            te_group = group[te_mask]
            
            # True Target is available at depth + 10m.
            # So warmup target is only known if target depth <= start_d + wu
            # Wait, df[t_col] represents target at depth+10m.
            # So the target is known to be in the warm-up only if the TARGET depth is <= start_d + wu.
            # That corresponds to depth + 10 <= start_d + wu.
            wu_eval_mask = (wu_group['Measured Depth m'] + 10.0) <= (start_d + wu)
            wu_eval_group = wu_group[wu_eval_mask]
            
            # Calculate warmup stats
            rops = wu_group['Rate of Penetration m/h'].values
            rop_mean = np.mean(rops)
            rop_std = np.std(rops)
            rop_volatility = np.std(np.diff(rops)) if len(rops)>1 else 0.0
            
            # Slope of ROP over depth
            if len(rops) > 2:
                slope, _, _, _, _ = linregress(wu_group['Measured Depth m'].values, rops)
            else: slope = 0.0
            
            wob_mean = np.mean(wu_group['Weight on Bit kkgf'].values)
            rpm_mean = np.mean(wu_group['Average Rotary Speed rpm'].values)
            
            # Warmup Errors
            wu_errors = {}
            if len(wu_eval_group) > 5:
                for c, cn in zip(candidates, cand_names):
                    wu_errors[cn] = mean_absolute_error(wu_eval_group[t_col], wu_eval_group[c])
            else:
                for cn in cand_names: wu_errors[cn] = np.nan
                
            # Test Errors (for labels)
            te_errors = {}
            if len(te_group) > 5:
                for c, cn in zip(candidates, cand_names):
                    te_errors[cn] = mean_absolute_error(te_group[t_col], te_group[c])
            else:
                for cn in cand_names: te_errors[cn] = np.nan
                
            stats_list.append({
                "Warmup": wu, "Well": well,
                "ROP_mean": rop_mean, "ROP_std": rop_std, "ROP_vol": rop_volatility, "ROP_slope": slope,
                "WOB_mean": wob_mean, "RPM_mean": rpm_mean,
                "WU_Err_Persistence": wu_errors.get('Persistence', np.nan),
                "WU_Err_EMA": wu_errors.get('EMA', np.nan),
                "WU_Err_LGBM": wu_errors.get('LGBM', np.nan),
                "TE_Err_Persistence": te_errors.get('Persistence', np.nan),
                "TE_Err_EMA": te_errors.get('EMA', np.nan),
                "TE_Err_LGBM": te_errors.get('LGBM', np.nan)
            })
            
    df_stats = pd.DataFrame(stats_list)
    
    # ----------------------------------------------------
    # MODEL SELECTION POLICIES
    # ----------------------------------------------------
    logger.info("Applying Model Selection Policies...")
    
    policies = ['Always_Persistence', 'Always_EMA', 'Always_LGBM', 'Warmup_Error_Gating', 'DecisionTree_Gating']
    results_list = []
    policy_choices = []
    
    features = ['ROP_mean', 'ROP_std', 'ROP_vol', 'ROP_slope', 'WOB_mean', 'RPM_mean']
    
    for wu in warmups:
        df_w = df_stats[df_stats['Warmup'] == wu].copy()
        
        # Determine winning model in Test (for DT training labels)
        te_cols = ['TE_Err_Persistence', 'TE_Err_EMA', 'TE_Err_LGBM']
        df_w['True_Best_Model'] = df_w[te_cols].idxmin(axis=1).str.replace('TE_Err_', '')
        
        for well in wells:
            row = df_w[df_w['Well'] == well].iloc[0]
            te_errs = {cn: row[f'TE_Err_{cn}'] for cn in cand_names}
            
            # Policy 1, 2, 3
            choices = {
                'Always_Persistence': 'Persistence',
                'Always_EMA': 'EMA',
                'Always_LGBM': 'LGBM'
            }
            
            # Policy 4: Warmup Error Gating
            wu_cols = ['WU_Err_Persistence', 'WU_Err_EMA', 'WU_Err_LGBM']
            if not np.isnan(row[wu_cols[0]]):
                best_wu = row[wu_cols].astype(float).idxmin().replace('WU_Err_', '')
                choices['Warmup_Error_Gating'] = best_wu
            else:
                # If warmup too small (e.g. 25m warmup gives 15m eval), default to LGBM
                choices['Warmup_Error_Gating'] = 'LGBM'
                
            # Policy 5: Decision Tree Gating (LOWO)
            # Train DT on other 6 wells using stats to predict True_Best_Model
            tr_df = df_w[df_w['Well'] != well].dropna(subset=features + ['True_Best_Model'])
            if len(tr_df) > 0:
                X_tr = tr_df[features].values
                y_tr = tr_df['True_Best_Model'].values
                dt = DecisionTreeClassifier(max_depth=1, random_state=42)
                dt.fit(X_tr, y_tr)
                X_te = row[features].values.reshape(1, -1)
                dt_pred = dt.predict(np.nan_to_num(X_te, nan=0.0))[0]
                choices['DecisionTree_Gating'] = dt_pred
            else:
                choices['DecisionTree_Gating'] = 'LGBM'
                
            for p in policies:
                chosen_mod = choices[p]
                policy_choices.append({
                    "Warmup": wu, "Well": well, "Policy": p, "Selected_Model": chosen_mod
                })
                # We need MAE, RMSE, R2, MedAE.
                # Since we already computed MAE per well test group, we can just grab it.
                # Wait, I only calculated MAE in stats_list! I need all metrics.
                # Let's recompute all metrics for the chosen model on the test set.
                group = df[df['well_id'] == well]
                depths = group['Measured Depth m'].values
                start_d = depths[0]
                te_group = group[depths > start_d + wu]
                
                if len(te_group) > 5:
                    y_t = te_group[t_col].values
                    # map chosen model to column
                    col_map = {'Persistence': p_col, 'EMA': 'EMA_2m', 'LGBM': 'LGBM'}
                    y_p = te_group[col_map[chosen_mod]].values
                    
                    mae, rmse, r2, medae = calc_metrics(y_t, y_p)
                    results_list.append({
                        "Warmup": wu, "Well": well, "Policy": p,
                        "Selected_Model": chosen_mod,
                        "MAE": mae, "RMSE": rmse, "R2": r2, "MedAE": medae
                    })
                    
    df_results = pd.DataFrame(results_list)
    df_choices = pd.DataFrame(policy_choices)
    
    df_results.to_csv(TABLES_DIR / "model_selection_by_well.csv", index=False)
    df_choices.to_csv(TABLES_DIR / "model_selection_policy.csv", index=False)
    
    # ----------------------------------------------------
    # SUMMARY AGGREGATION
    # ----------------------------------------------------
    logger.info("Computing Macro Aggregates...")
    summary_list = []
    for wu in warmups:
        for p in policies:
            sub = df_results[(df_results['Warmup'] == wu) & (df_results['Policy'] == p)]
            if len(sub) == 0: continue
            
            # Find best fixed predictor MAE for this warmup
            best_fixed_mae = np.min([
                df_results[(df_results['Warmup']==wu)&(df_results['Policy']=='Always_Persistence')]['MAE'].mean(),
                df_results[(df_results['Warmup']==wu)&(df_results['Policy']=='Always_EMA')]['MAE'].mean(),
                df_results[(df_results['Warmup']==wu)&(df_results['Policy']=='Always_LGBM')]['MAE'].mean()
            ])
            
            mean_mae = sub['MAE'].mean()
            imp_vs_best = best_fixed_mae - mean_mae
            imp_vs_pers = df_results[(df_results['Warmup']==wu)&(df_results['Policy']=='Always_Persistence')]['MAE'].mean() - mean_mae
            
            wins_vs_best = (sub['MAE'].values < df_results[(df_results['Warmup']==wu)&(df_results['Policy']=='Always_LGBM')]['MAE'].values).sum()
            
            summary_list.append({
                "Warmup": wu, "Policy": p, "Macro_MAE": mean_mae,
                "Median_Well_MAE": sub['MAE'].median(),
                "Imp_vs_Best_Fixed": imp_vs_best,
                "Imp_vs_Persist": imp_vs_pers,
                "Wins_vs_LGBM": wins_vs_best
            })
            
    df_sum = pd.DataFrame(summary_list)
    df_sum.to_csv(TABLES_DIR / "model_selection_summary.csv", index=False)
    
    # ----------------------------------------------------
    # VISUALIZATION
    # ----------------------------------------------------
    logger.info("Generating visuals...")
    plt.figure(figsize=(10,6))
    sns.barplot(data=df_sum[df_sum['Warmup']==50.0], x='Policy', y='Macro_MAE')
    plt.title("Macro MAE by Selection Policy (50m Warmup)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "policy_mae_50m.png")
    plt.close()
    
    plt.figure(figsize=(10,6))
    sns.lineplot(data=df_sum, x='Warmup', y='Macro_MAE', hue='Policy', marker='o')
    plt.title("Policy Macro MAE vs Warmup Length")
    plt.xlabel("Warm-up Length (m)")
    plt.ylabel("Macro MAE (m/h)")
    plt.grid(True)
    plt.savefig(FIG_DIR / "policy_vs_warmup.png")
    plt.close()
    
    # ----------------------------------------------------
    # MARKDOWN REPORT
    # ----------------------------------------------------
    md_content = f"""# Model Selection / Gating Study

## 1. Executive Summary
- **Hypothesis**: For a new unseen well, different predictors may be optimal depending on its early observed behavior. A lightweight model-selection mechanism may outperform committing to one global predictor.
- **Protocol**: 7-well LOWO evaluation. The candidate selection policy is **frozen** after observing a causal warm-up period (25m to 200m).
- **Candidates**: Persistence, EMA (2m), and Static ROP-history LightGBM.

## 2. Macro Performance Summary
The following table summarizes the Macro MAE across policies for different warm-up lengths. A positive `Imp vs Best Fixed` means the gating policy successfully outperformed the best single candidate globally.

{df_sum[['Warmup', 'Policy', 'Macro_MAE', 'Imp_vs_Best_Fixed', 'Wins_vs_LGBM']].to_markdown(index=False)}

## 3. Analysis of Policies (50m Warmup)
Focusing on the 50m warm-up period:

- **Always LGBM**: MAE = {df_sum[(df_sum['Warmup']==50.0)&(df_sum['Policy']=='Always_LGBM')]['Macro_MAE'].values[0]:.2f}
- **Warmup Error Gating**: MAE = {df_sum[(df_sum['Warmup']==50.0)&(df_sum['Policy']=='Warmup_Error_Gating')]['Macro_MAE'].values[0]:.2f}
- **Decision Tree Gating**: MAE = {df_sum[(df_sum['Warmup']==50.0)&(df_sum['Policy']=='DecisionTree_Gating')]['Macro_MAE'].values[0]:.2f}

### Policy Breakdown:
1. **Warmup Error Gating**: Evaluating the candidates on the observed 50m and picking the lowest-error model for the rest of the well.
2. **Decision Tree Gating**: A single-split decision tree trained on the *other 6 wells'* early statistics (volatility, slope, ROP mean) to predict the best model, applied causally to the unseen well.

## 4. Final Conclusion
**1. Does model gating outperform a single global predictor?**
[To be written based on results]

**2. Which gating strategy is best?**
[To be written based on results]

**3. Is Early-Well Behavior Predictive of the Best Model?**
[To be written based on results]
"""
    with open(REPORTS_DIR / "model_selection_experiment.md", "w") as f:
        f.write(md_content)
    logger.info("Done.")

if __name__ == "__main__":
    main()
