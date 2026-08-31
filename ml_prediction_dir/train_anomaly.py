import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import IsolationForest
import joblib
import warnings

warnings.filterwarnings('ignore')

os.makedirs('ml_prediction_dir/graphs', exist_ok=True)
os.makedirs('ml_prediction_dir/metrics', exist_ok=True)
os.makedirs('ml_prediction_dir/saved_models', exist_ok=True)

def train_anomaly_detection():
    print("--- Training Anomaly Detection on Volve Dataset ---")
    df = pd.read_parquet('data/processed/real_training/mud_loss_real_v1.parquet')
    
    # Sort by well and depth
    if 'onset_md' in df.columns:
        df = df.sort_values(by=['well_id', 'onset_md']).reset_index(drop=True)
    
    target_col = 'is_event'
    
    # Exclude non-generalizable features and metadata
    exclude_cols = [target_col, 'well_id', 'ddr_activity_phase', 'onset_md', 'cutoff_md']
    features_df = df.drop(columns=exclude_cols, errors='ignore')
    features_df = features_df.select_dtypes(include=[np.number])
    
    # Drop rows with NaN
    valid_idx = features_df.dropna().index
    df_clean = df.loc[valid_idx].copy()
    X = features_df.loc[valid_idx].copy()
    y = df_clean[target_col].copy()
    
    # Define "normal" data: exclude events and a small window around them
    # For simplicity, we exclude exactly the rows where is_event == 1
    # If we want a window, we can exclude rows within +/- 25m of an event
    normal_idx = (y == 0)
    
    # Optional: exclude +/- 25m window around events if onset_md is available
    if 'onset_md' in df_clean.columns:
        event_mds = df_clean.loc[y == 1, ['well_id', 'onset_md']]
        for _, row in event_mds.iterrows():
            w_id = row['well_id']
            e_md = row['onset_md']
            # condition to exclude
            in_window = (df_clean['well_id'] == w_id) & (df_clean['onset_md'].between(e_md - 25, e_md + 25))
            normal_idx = normal_idx & (~in_window)

    X_train_normal = X[normal_idx]
    
    print(f"Training Isolation Forest on {len(X_train_normal)} normal samples...")
    iso_forest = IsolationForest(contamination='auto', n_estimators=200, random_state=42)
    iso_forest.fit(X_train_normal)
    
    # Score the full dataset
    # decision_function: lower score = more anomalous. We flip sign so higher = anomalous
    scores = -iso_forest.decision_function(X)
    df_clean['anomaly_score'] = scores
    
    # Thresholding & Stats
    # e.g., top 2% of scores across the dataset
    threshold_98 = np.percentile(scores, 98)
    df_clean['is_high_risk'] = df_clean['anomaly_score'] > threshold_98
    
    # Calculate ranks (1 = highest anomaly score)
    ranks = df_clean['anomaly_score'].rank(ascending=False)
    df_clean['anomaly_rank'] = ranks

    # Rank check for events
    event_rows = df_clean[y == 1]
    total_rows = len(df_clean)
    
    print("\n--- Anomaly Detection Results ---")
    event_stats = []
    for idx, row in event_rows.iterrows():
        rank = row['anomaly_rank']
        percentile = (rank / total_rows) * 100
        print(f"Event at Well: {row.get('well_id', 'Unknown')}, MD: {row.get('onset_md', 'Unknown')}m")
        print(f" -> Anomaly Rank: {rank}/{total_rows} (Top {percentile:.2f}%)")
        event_stats.append({
            'well_id': row.get('well_id', 'Unknown'),
            'onset_md': row.get('onset_md', 'Unknown'),
            'anomaly_score': row['anomaly_score'],
            'rank': rank,
            'percentile_top': percentile
        })
    
    # False positive rate
    normal_rows = df_clean[y == 0]
    false_positives = normal_rows['is_high_risk'].sum()
    fpr = (false_positives / len(normal_rows)) * 100
    print(f"\nFalse Positive Rate (using Top 2% threshold): {fpr:.2f}% ({false_positives}/{len(normal_rows)} normal rows flagged)")
    
    # Save stats
    pd.DataFrame(event_stats).to_csv('ml_prediction_dir/metrics/volve_anomaly_events_stats.csv', index=False)
    
    # Feature-level explanation (Z-scores)
    print("\n--- Feature-Level Explanations (Z-Scores) ---")
    normal_mean = X_train_normal.mean()
    normal_std = X_train_normal.std().replace(0, 1e-9) # Avoid div by zero
    
    for idx, row in event_rows.iterrows():
        event_features = X.loc[idx]
        z_scores = np.abs((event_features - normal_mean) / normal_std)
        top_features = z_scores.sort_values(ascending=False).head(3)
        print(f"Event at MD: {row.get('onset_md', 'Unknown')}m")
        for feat, z in top_features.items():
            print(f"  - {feat}: Z-score = {z:.2f}")
    
    # Save Model
    joblib.dump(iso_forest, 'ml_prediction_dir/saved_models/volve_iso_forest.joblib')
    joblib.dump(list(X.columns), 'ml_prediction_dir/saved_models/volve_iso_features.joblib')
    
    # Plotting
    event_wells = event_rows['well_id'].unique() if 'well_id' in event_rows.columns else []
    
    for well in event_wells:
        well_df = df_clean[df_clean['well_id'] == well].copy()
        well_df = well_df.sort_values('onset_md')
        
        plt.figure(figsize=(12, 6))
        plt.plot(well_df['onset_md'], well_df['anomaly_score'], label='Anomaly Score', color='blue', alpha=0.7)
        plt.axhline(threshold_98, color='orange', linestyle='--', label='Top 2% High-Risk Threshold')
        
        # Mark true events
        well_events = well_df[well_df[target_col] == 1]
        for _, ev in well_events.iterrows():
            plt.axvline(ev['onset_md'], color='red', linestyle='-', linewidth=2, label='True Mud Loss Event')
            
        plt.title(f"Anomaly Score over Depth - Well {well}")
        plt.xlabel("Measured Depth (m)")
        plt.ylabel("Anomaly Score (Higher = More Anomalous)")
        
        # Remove duplicate labels in legend
        handles, labels = plt.gca().get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        plt.legend(by_label.values(), by_label.keys())
        
        plt.tight_layout()
        safe_well_name = str(well).replace('/', '_')
        plt.savefig(f'ml_prediction_dir/graphs/anomaly_score_{safe_well_name}.png')
        plt.close()
        
    print(f"\nGenerated Anomaly Plots for {len(event_wells)} wells in ml_prediction_dir/graphs/")

if __name__ == '__main__':
    train_anomaly_detection()
