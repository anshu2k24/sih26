import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import IsolationForest
import warnings

warnings.filterwarnings('ignore')

print("--- Seed Robustness Check (Volve Anomaly) ---")
df = pd.read_parquet('data/processed/real_training/mud_loss_real_v1.parquet')

target_col = 'is_event'
exclude_cols = [target_col, 'well_id', 'ddr_activity_phase', 'onset_md', 'cutoff_md']
features_df = df.drop(columns=exclude_cols, errors='ignore').select_dtypes(include=[np.number])

valid_idx = features_df.dropna().index
df_clean = df.loc[valid_idx].copy()
X = features_df.loc[valid_idx].reset_index(drop=True)
y = df_clean[target_col].reset_index(drop=True)

seeds = [0, 1, 42, 123, 2024]
results = []

for seed in seeds:
    oof_iso = np.zeros(len(y))
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    
    for train_idx, test_idx in skf.split(X, y):
        X_train, y_train = X.loc[train_idx], y.loc[train_idx]
        X_test = X.loc[test_idx]
        
        normal_train_idx = train_idx[y_train == 0]
        X_train_normal = X.loc[normal_train_idx]
        
        iso = IsolationForest(contamination=0.02, n_estimators=200, random_state=42) # Keep IF random_state constant, just change split
        iso.fit(X_train_normal)
        
        preds = iso.predict(X_test)
        oof_iso[test_idx] = (preds == -1).astype(int)
        
    caught = (oof_iso[y == 1] == 1).sum()
    results.append(caught)
    print(f"Seed {seed:4d}: Caught {caught}/3")

print(f"\nSummary: Caught {min(results)}-{max(results)} out of 3 across {len(seeds)} CV seeds.")
print(f"Median: {np.median(results)}/3")
