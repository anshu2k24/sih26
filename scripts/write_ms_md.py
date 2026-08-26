import pandas as pd
from pathlib import Path
REPO_ROOT = Path("/home/bhavshank/code/sih")
TABLES_DIR = REPO_ROOT / "reports/tables"
REPORTS_DIR = REPO_ROOT / "reports"

df_sum = pd.read_csv(TABLES_DIR / "model_selection_summary.csv")

# Extract 50m metrics
lgbm_50 = df_sum[(df_sum['Warmup']==50.0)&(df_sum['Policy']=='Always_LGBM')]['Macro_MAE'].values[0]
wu_err_50 = df_sum[(df_sum['Warmup']==50.0)&(df_sum['Policy']=='Warmup_Error_Gating')]['Macro_MAE'].values[0]
dt_50 = df_sum[(df_sum['Warmup']==50.0)&(df_sum['Policy']=='DecisionTree_Gating')]['Macro_MAE'].values[0]

# Extract 100m metrics
lgbm_100 = df_sum[(df_sum['Warmup']==100.0)&(df_sum['Policy']=='Always_LGBM')]['Macro_MAE'].values[0]
wu_err_100 = df_sum[(df_sum['Warmup']==100.0)&(df_sum['Policy']=='Warmup_Error_Gating')]['Macro_MAE'].values[0]
dt_100 = df_sum[(df_sum['Warmup']==100.0)&(df_sum['Policy']=='DecisionTree_Gating')]['Macro_MAE'].values[0]


md_content = f"""# Model Selection / Gating Study

## 1. Executive Summary
- **Hypothesis**: For a new unseen well, different predictors may be optimal depending on its early observed behavior. A lightweight model-selection mechanism may outperform committing to one global predictor.
- **Protocol**: 7-well LOWO evaluation. The candidate selection policy is **frozen** after observing a causal warm-up period (25m to 200m).
- **Candidates**: Persistence, EMA (2m), and Static ROP-history LightGBM.

## 2. Macro Performance Summary
The following table summarizes the Macro MAE across policies for different warm-up lengths. A positive `Imp vs Best Fixed` means the gating policy successfully outperformed the best single candidate globally.

{df_sum[['Warmup', 'Policy', 'Macro_MAE', 'Imp_vs_Best_Fixed', 'Wins_vs_LGBM']].to_markdown(index=False)}

## 3. Analysis of Policies (50m & 100m Warmup)
Focusing on the 50m warm-up period:
- **Always LGBM**: MAE = {lgbm_50:.2f}
- **Warmup Error Gating**: MAE = {wu_err_50:.2f}
- **Decision Tree Gating**: MAE = {dt_50:.2f}

Focusing on the 100m warm-up period:
- **Always LGBM**: MAE = {lgbm_100:.2f}
- **Warmup Error Gating**: MAE = {wu_err_100:.2f}
- **Decision Tree Gating**: MAE = {dt_100:.2f}

### Policy Breakdown:
1. **Warmup Error Gating**: Evaluating the candidates on the observed warmup period and picking the lowest-error model for the rest of the well.
2. **Decision Tree Gating**: A single-split decision tree trained on the *other 6 wells'* early statistics (volatility, slope, ROP mean) to predict the best model, applied causally to the unseen well.

## 4. Final Conclusion
**1. Does model gating outperform a single global predictor?**
Only occasionally, and it is highly sensitive to the warm-up length. At 100m of observation, Decision Tree gating successfully chose models that beat the static global model (MAE {dt_100:.2f} vs {lgbm_100:.2f}). However, at 50m and 200m, gating performed worse than simply committing to `Always LGBM`. 

**2. Which gating strategy is best?**
Both strategies are flawed due to the tiny sample size (7 wells). Warmup Error Gating is highly volatile because the winning model in the first 50m is rarely the winning model for the next 3000m. Decision Tree Gating (using early statistics like ROP volatility) shows flashes of promise but is too brittle.

**3. Is Early-Well Behavior Predictive of the Best Model?**
No. Early well behavior (the first 50m-100m) is not sufficiently representative of the geological regimes encountered thousands of meters deeper. Attempting to lock in a single model based on early behavior is brittle. 

**Ultimate Finding**: The Static ROP-history LightGBM is incredibly robust as a global autoregressive predictor. Any future online system must continuously adapt *during* drilling (e.g. streaming weights), rather than simply selecting a fixed model at the start of the well.
"""
with open(REPORTS_DIR / "model_selection_experiment.md", "w") as f:
    f.write(md_content)
