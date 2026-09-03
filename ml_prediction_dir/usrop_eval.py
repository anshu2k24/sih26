import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_squared_error
import xgboost as xgb
import lightgbm as lgb
import shap
import warnings

warnings.filterwarnings('ignore')

print("--- USROP Leakage Check (GroupKFold & Depth Dropped) ---")

# Load USROP dataset
df = pd.read_parquet('data/processed/usrop/usrop_clean.parquet')

# Features and target
target_col = 'Rate of Penetration m/h'
well_col = 'well_id'

# The user explicitly told us to drop depth features to check for leakage
leakage_cols = ['Measured Depth m', 'Hole Depth (TVD) m']
exclude_cols = [target_col, well_col, 'filename', 'sha256', 'MD_step'] + leakage_cols

features_df = df.drop(columns=exclude_cols, errors='ignore').select_dtypes(include=[np.number])

valid_idx = features_df.dropna().index
df_clean = df.loc[valid_idx].copy()
X = features_df.loc[valid_idx].reset_index(drop=True)
y = df_clean[target_col].reset_index(drop=True)
wells = df_clean[well_col].reset_index(drop=True)

print(f"Dataset Size: {len(X)} rows")
print(f"Unique Wells: {wells.nunique()}")

# GroupKFold evaluation
gkf = GroupKFold(n_splits=min(5, wells.nunique()))
oof_xgb = np.zeros(len(y))
oof_lgb = np.zeros(len(y))

# Retrain both models across GroupKFold
for train_idx, test_idx in gkf.split(X, y, groups=wells):
    X_train, y_train = X.loc[train_idx], y.loc[train_idx]
    X_test, y_test = X.loc[test_idx], y.loc[test_idx]
    
    # XGBoost
    xgb_reg = xgb.XGBRegressor(random_state=42, n_estimators=100)
    xgb_reg.fit(X_train, y_train)
    oof_xgb[test_idx] = xgb_reg.predict(X_test)
    
    # LightGBM
    lgb_reg = lgb.LGBMRegressor(random_state=42, n_estimators=100)
    lgb_reg.fit(X_train, y_train)
    oof_lgb[test_idx] = lgb_reg.predict(X_test)

# Calculate R2 and MSE
xgb_r2 = r2_score(y, oof_xgb)
xgb_mse = mean_squared_error(y, oof_xgb)

lgb_r2 = r2_score(y, oof_lgb)
lgb_mse = mean_squared_error(y, oof_lgb)

print("\n--- Leakage Check Results (Cross-Well R2 without Depth) ---")
print(f"XGBoost R2 : {xgb_r2:.4f} (MSE: {xgb_mse:.2f})")
print(f"LightGBM R2: {lgb_r2:.4f} (MSE: {lgb_mse:.2f})")

# SHAP Analysis on full dataset (XGBoost)
print("\n--- Running SHAP Analysis (XGBoost) ---")
xgb_final = xgb.XGBRegressor(random_state=42, n_estimators=100)
xgb_final.fit(X, y)

# We use a sample if dataset is too large, but tree explainer is fast
explainer = shap.TreeExplainer(xgb_final)
shap_values = explainer.shap_values(X)

# Calculate mean absolute SHAP values for importance ranking
mean_abs_shap = np.abs(shap_values).mean(axis=0)
shap_importance = pd.DataFrame({
    'Feature': X.columns,
    'Importance': mean_abs_shap
}).sort_values(by='Importance', ascending=False)

print("\nTop 10 Stable Features (SHAP Importance):")
for idx, row in shap_importance.head(10).iterrows():
    print(f"  - {row['Feature']}: {row['Importance']:.4f}")

