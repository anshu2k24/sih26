import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score
import lightgbm as lgb
import shap
import warnings

warnings.filterwarnings('ignore')

print("--- USROP Diagnostics & LightGBM SHAP ---")

# Load USROP dataset
df = pd.read_parquet('data/processed/usrop/usrop_clean.parquet')

# Features and target
target_col = 'Rate of Penetration m/h'
well_col = 'well_id'
depth_col = 'Measured Depth m'
gamma_col = 'USROP Gamma gAPI'

# 1. Diagnose Cross-Well Variance
print("\n[Well Characteristics]")
well_stats = df.groupby(well_col).agg(
    Rows=('well_id', 'count'),
    Min_Depth=(depth_col, 'min'),
    Max_Depth=(depth_col, 'max'),
    Mean_ROP=(target_col, 'mean'),
    Mean_Gamma=(gamma_col, 'mean')
).reset_index()

for _, row in well_stats.iterrows():
    print(f"Well {row[well_col]}: {row['Rows']} rows | MD: {row['Min_Depth']:.1f}-{row['Max_Depth']:.1f}m | Mean ROP: {row['Mean_ROP']:.2f} | Mean Gamma: {row['Mean_Gamma']:.2f}")

# Exclude raw depth features to avoid leakage
leakage_cols = ['Measured Depth m', 'Hole Depth (TVD) m']
exclude_cols = [target_col, well_col, 'filename', 'sha256', 'MD_step'] + leakage_cols

features_df = df.drop(columns=exclude_cols, errors='ignore').select_dtypes(include=[np.number])
valid_idx = features_df.dropna().index
df_clean = df.loc[valid_idx].copy()
X = features_df.loc[valid_idx].reset_index(drop=True)
y = df_clean[target_col].reset_index(drop=True)
wells = df_clean[well_col].reset_index(drop=True)

# 2. Per-Fold R2 using LightGBM
print("\n[Per-Fold LightGBM Performance (GroupKFold)]")
gkf = GroupKFold(n_splits=wells.nunique())
oof_lgb = np.zeros(len(y))

fold = 1
fold_r2s = []
for train_idx, test_idx in gkf.split(X, y, groups=wells):
    X_train, y_train = X.loc[train_idx], y.loc[train_idx]
    X_test, y_test = X.loc[test_idx], y.loc[test_idx]
    test_wells = wells.loc[test_idx].unique()
    
    lgb_reg = lgb.LGBMRegressor(random_state=42, n_estimators=100, force_col_wise=True)
    lgb_reg.fit(X_train, y_train)
    preds = lgb_reg.predict(X_test)
    oof_lgb[test_idx] = preds
    
    fold_r2 = r2_score(y_test, preds)
    fold_r2s.append(fold_r2)
    print(f"Fold {fold} (Wells: {list(test_wells)}): R2 = {fold_r2:.4f}")
    fold += 1

global_r2 = r2_score(y, oof_lgb)
print(f"-> Global Out-of-Well R2: {global_r2:.4f}")

# 3. LightGBM SHAP Analysis
print("\n[LightGBM SHAP Analysis]")
lgb_final = lgb.LGBMRegressor(random_state=42, n_estimators=100, force_col_wise=True)
lgb_final.fit(X, y)

# shap.TreeExplainer on LightGBM
explainer = shap.TreeExplainer(lgb_final)
# Sample to save time if necessary, but 190k is usually fast for LGBM TreeExplainer
# Using a 10% sample for SHAP calculation speed
sample_idx = np.random.choice(X.index, size=int(len(X)*0.1), replace=False)
X_sample = X.loc[sample_idx]
shap_values = explainer.shap_values(X_sample)

mean_abs_shap = np.abs(shap_values).mean(axis=0)
shap_importance = pd.DataFrame({
    'Feature': X.columns,
    'Importance': mean_abs_shap
}).sort_values(by='Importance', ascending=False)

for idx, row in shap_importance.iterrows():
    print(f"  - {row['Feature']}: {row['Importance']:.4f}")
