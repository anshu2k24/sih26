import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score
import lightgbm as lgb
import warnings

warnings.filterwarnings('ignore')

print("--- USROP Single-Pass Relative Feature Engineering ---")

df = pd.read_parquet('data/processed/usrop/usrop_clean.parquet')
df = df.sort_values(by=['well_id', 'Measured Depth m']).reset_index(drop=True)

# 1. Feature Engineering (Ratios)
df['torque_wob_ratio'] = df['Average Surface Torque kN.m'] / (df['Weight on Bit kkgf'] + 1e-6)
df['flow_spp_ratio'] = df['Mud Flow In L/min'] / (df['Average Standpipe Pressure kPa'] + 1e-6)
df['wob_hookload_ratio'] = df['Weight on Bit kkgf'] / (df['Average Hookload kkgf'] + 1e-6)

# 2. Feature Engineering (Rolling Rate of Change per well)
df['torque_delta_5'] = df.groupby('well_id')['Average Surface Torque kN.m'].diff(5).fillna(0)
df['wob_delta_5'] = df.groupby('well_id')['Weight on Bit kkgf'].diff(5).fillna(0)
df['hookload_delta_5'] = df.groupby('well_id')['Average Hookload kkgf'].diff(5).fillna(0)
df['spp_delta_5'] = df.groupby('well_id')['Average Standpipe Pressure kPa'].diff(5).fillna(0)

# Setup for ML
target_col = 'Rate of Penetration m/h'
well_col = 'well_id'
leakage_cols = ['Measured Depth m', 'Hole Depth (TVD) m']
exclude_cols = [target_col, well_col, 'filename', 'sha256', 'MD_step'] + leakage_cols

features_df = df.drop(columns=exclude_cols, errors='ignore').select_dtypes(include=[np.number])
valid_idx = features_df.dropna().index
df_clean = df.loc[valid_idx].copy()
X = features_df.loc[valid_idx].reset_index(drop=True)
y = df_clean[target_col].reset_index(drop=True)
wells = df_clean[well_col].reset_index(drop=True)

print(f"Dataset Size: {len(X)} rows with {X.shape[1]} features (including engineered).")

# 3. GroupKFold Eval
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
    fold_r2s.append((list(test_wells)[0], fold_r2))
    print(f"Fold {fold} (Well: {list(test_wells)[0]}): R2 = {fold_r2:.4f}")
    fold += 1

global_r2 = r2_score(y, oof_lgb)
negative_folds = sum(1 for _, r2 in fold_r2s if r2 < 0)

print(f"\n-> Global Out-of-Well R2: {global_r2:.4f}")
print(f"-> Negative Folds: {negative_folds} out of {wells.nunique()} wells")
