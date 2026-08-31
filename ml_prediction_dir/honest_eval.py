import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import xgboost as xgb
import lightgbm as lgb
import warnings

warnings.filterwarnings('ignore')

print("--- Leave-One-Well-Out (LOWO) Honest Evaluation ---")
df = pd.read_parquet('data/processed/real_training/mud_loss_real_v1.parquet')

# Sort by well and depth
if 'onset_md' in df.columns:
    df = df.sort_values(by=['well_id', 'onset_md']).reset_index(drop=True)

target_col = 'is_event'
exclude_cols = [target_col, 'well_id', 'ddr_activity_phase', 'onset_md', 'cutoff_md']
features_df = df.drop(columns=exclude_cols, errors='ignore').select_dtypes(include=[np.number])

valid_idx = features_df.dropna().index
df_clean = df.loc[valid_idx].copy()
X = features_df.loc[valid_idx].copy()
y = df_clean[target_col].copy()
wells = df_clean['well_id'].copy()

# The only events are in well 15/9-F-15. So we use that as the test set.
test_well = '15/9-F-15'
train_idx = (wells != test_well)
test_idx = (wells == test_well)

X_train, y_train = X[train_idx], y[train_idx]
X_test, y_test = X[test_idx], y[test_idx]

print(f"Training on {len(X_train)} samples (Events: {y_train.sum()})")
print(f"Testing on {len(X_test)} samples (Events: {y_test.sum()})")

# 1. Isolation Forest (A priori contamination = 0.02)
# Trained only on normal data from train set (all y_train are 0 anyway)
iso_forest = IsolationForest(contamination=0.02, n_estimators=200, random_state=42)
iso_forest.fit(X_train)
iso_preds_test = iso_forest.predict(X_test)
iso_flags = (iso_preds_test == -1).astype(int)

# Score full test set
iso_scores = -iso_forest.decision_function(X_test)

# 2. Supervised Models
# They are trained on a set with 0 positive examples. 
# This will likely fail or just predict 0.
try:
    xgb_clf = xgb.XGBClassifier(random_state=42, n_estimators=100)
    xgb_clf.fit(X_train, y_train)
    xgb_flags = xgb_clf.predict(X_test)
except Exception as e:
    xgb_flags = np.zeros(len(X_test))
    print("XGBoost failed to fit due to lack of positive class:", e)

try:
    lgb_clf = lgb.LGBMClassifier(random_state=42, n_estimators=100)
    lgb_clf.fit(X_train, y_train)
    lgb_flags = lgb_clf.predict(X_test)
except Exception as e:
    lgb_flags = np.zeros(len(X_test))
    print("LightGBM failed to fit due to lack of positive class:", e)

# Results Analysis on Test Well (15/9-F-15)
df_test = df_clean[test_idx].copy()
df_test['iso_flag'] = iso_flags
df_test['xgb_flag'] = xgb_flags
df_test['lgb_flag'] = lgb_flags
df_test['iso_score'] = iso_scores
# Rank within test set? Or rank globally? Let's just output raw scores.

total_events = y_test.sum()
iso_caught = (df_test[y_test == 1]['iso_flag'] == 1).sum()
xgb_caught = (df_test[y_test == 1]['xgb_flag'] == 1).sum()
lgb_caught = (df_test[y_test == 1]['lgb_flag'] == 1).sum()

print("\n[Catch Rate on True Events (Test Well: 15/9-F-15)]")
print(f"Isolation Forest: Caught {iso_caught}/{total_events}")
print(f"XGBoost:          Caught {xgb_caught}/{total_events}")
print(f"LightGBM:         Caught {lgb_caught}/{total_events}")

print("\n[Event Specific Details (Isolation Forest)]")
for idx, row in df_test[y_test == 1].iterrows():
    md = row.get('onset_md', 'Unknown')
    print(f"Event at MD {md}m: {'FLAGGED' if row['iso_flag'] == 1 else 'MISSED'} (Score {row['iso_score']:.4f})")

