import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import IsolationForest
import xgboost as xgb
import lightgbm as lgb
import warnings

warnings.filterwarnings('ignore')

print("--- Rigorous 5-Fold Cross-Validation ---")
df = pd.read_parquet('data/processed/real_training/mud_loss_real_v1.parquet')

target_col = 'is_event'
exclude_cols = [target_col, 'well_id', 'ddr_activity_phase', 'onset_md', 'cutoff_md']
features_df = df.drop(columns=exclude_cols, errors='ignore').select_dtypes(include=[np.number])

valid_idx = features_df.dropna().index
df_clean = df.loc[valid_idx].copy()
X = features_df.loc[valid_idx].reset_index(drop=True)
y = df_clean[target_col].reset_index(drop=True)

oof_iso = np.zeros(len(y))
oof_xgb = np.zeros(len(y))
oof_lgb = np.zeros(len(y))
iso_scores = np.zeros(len(y))

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

for fold, (train_idx, test_idx) in enumerate(skf.split(X, y)):
    X_train, y_train = X.loc[train_idx], y.loc[train_idx]
    X_test, y_test = X.loc[test_idx], y.loc[test_idx]
    
    pos_count = y_train.sum()
    scale_pos_weight = (len(y_train) - pos_count) / pos_count if pos_count > 0 else 1
    
    # XGBoost
    xgb_clf = xgb.XGBClassifier(random_state=42, scale_pos_weight=scale_pos_weight, n_estimators=100)
    xgb_clf.fit(X_train, y_train)
    oof_xgb[test_idx] = xgb_clf.predict(X_test)
    
    # LightGBM
    lgb_clf = lgb.LGBMClassifier(random_state=42, scale_pos_weight=scale_pos_weight, n_estimators=100)
    lgb_clf.fit(X_train, y_train)
    oof_lgb[test_idx] = lgb_clf.predict(X_test)
    
    # Isolation Forest
    normal_train_idx = train_idx[y_train == 0]
    X_train_normal = X.loc[normal_train_idx]
    
    iso = IsolationForest(contamination=0.02, n_estimators=200, random_state=42)
    iso.fit(X_train_normal)
    
    # Predict (-1 is anomaly, 1 is normal) -> map to 1 (anomaly) and 0 (normal)
    preds = iso.predict(X_test)
    oof_iso[test_idx] = (preds == -1).astype(int)
    iso_scores[test_idx] = -iso.decision_function(X_test)

df_clean['iso_flag'] = oof_iso
df_clean['xgb_flag'] = oof_xgb
df_clean['lgb_flag'] = oof_lgb
df_clean['iso_score'] = iso_scores
df_clean['iso_rank'] = df_clean['iso_score'].rank(ascending=False)

total_normal = (y == 0).sum()
total_events = (y == 1).sum()

print(f"\nTotal Normal: {total_normal}, Total Events: {total_events}")

def print_metrics(model_name, flag_col):
    caught = (df_clean[y == 1][flag_col] == 1).sum()
    fp = (df_clean[y == 0][flag_col] == 1).sum()
    fpr = (fp / total_normal) * 100
    print(f"{model_name:18}: Caught {caught}/{total_events} (FPR: {fpr:.2f}% | False Positives: {fp})")

print("\n[Out-of-Fold Cross-Validation Catch Rate]")
print_metrics("Isolation Forest", "iso_flag")
print_metrics("XGBoost", "xgb_flag")
print_metrics("LightGBM", "lgb_flag")

print("\n[Event Specific Details (Isolation Forest)]")
for idx, row in df_clean[y == 1].iterrows():
    md = row.get('onset_md', 'Unknown')
    rank = row['iso_rank']
    print(f"Event at MD {md}m: {'FLAGGED' if row['iso_flag'] == 1 else 'MISSED'} (Score {row['iso_score']:.4f}, Rank {rank}/{len(df_clean)})")

