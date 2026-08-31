import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score, f1_score, roc_auc_score, confusion_matrix
import xgboost as xgb
import lightgbm as lgb
import joblib
import warnings

warnings.filterwarnings('ignore')

os.makedirs('ml_prediction_dir/graphs', exist_ok=True)
os.makedirs('ml_prediction_dir/metrics', exist_ok=True)
os.makedirs('ml_prediction_dir/saved_models', exist_ok=True)

def plot_feature_importance(model, title, filepath):
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
        feature_names = model.feature_name_ if hasattr(model, 'feature_name_') else model.feature_names_in_
        
        # Get top 15 features
        indices = np.argsort(importances)[::-1][:15]
        
        plt.figure(figsize=(10, 6))
        plt.title(title)
        plt.bar(range(len(indices)), importances[indices], align="center")
        plt.xticks(range(len(indices)), [feature_names[i] for i in indices], rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(filepath)
        plt.close()

def train_usrop():
    print("--- Training on USROP Dataset (Regression) ---")
    df = pd.read_parquet('data/processed/usrop/usrop_clean.parquet')
    
    target_col = 'Rate of Penetration m/h'
    features = df.drop(columns=[target_col, 'well_id', 'filename', 'sha256', 'MD_step'], errors='ignore')
    
    df_clean = pd.concat([features, df[target_col]], axis=1).dropna()
    X = df_clean.drop(columns=[target_col])
    y = df_clean[target_col]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training LightGBM Regressor...")
    lgb_reg = lgb.LGBMRegressor(random_state=42, n_estimators=100)
    lgb_reg.fit(X_train, y_train)
    lgb_pred = lgb_reg.predict(X_test)
    
    print("Training XGBoost Regressor...")
    xgb_reg = xgb.XGBRegressor(random_state=42, n_estimators=100)
    xgb_reg.fit(X_train, y_train)
    xgb_pred = xgb_reg.predict(X_test)
    
    metrics = {
        'Model': ['LightGBM', 'XGBoost'],
        'MSE': [mean_squared_error(y_test, lgb_pred), mean_squared_error(y_test, xgb_pred)],
        'R2_Score': [r2_score(y_test, lgb_pred), r2_score(y_test, xgb_pred)]
    }
    
    metrics_df = pd.DataFrame(metrics)
    metrics_df.to_csv('ml_prediction_dir/metrics/usrop_metrics.csv', index=False)
    print(metrics_df.to_string(index=False))
    
    # Save the models
    joblib.dump(lgb_reg, 'ml_prediction_dir/saved_models/usrop_lgbm.joblib')
    joblib.dump(xgb_reg, 'ml_prediction_dir/saved_models/usrop_xgb.joblib')
    
    # Save feature names for FastAPI payload validation
    joblib.dump(list(X.columns), 'ml_prediction_dir/saved_models/usrop_features.joblib')
    
    plot_feature_importance(lgb_reg, 'LightGBM Feature Importance (USROP)', 'ml_prediction_dir/graphs/usrop_lgbm_importance.png')
    plot_feature_importance(xgb_reg, 'XGBoost Feature Importance (USROP)', 'ml_prediction_dir/graphs/usrop_xgb_importance.png')
    
    plt.figure(figsize=(8, 6))
    plt.scatter(y_test, lgb_pred, alpha=0.3, label='LightGBM')
    plt.scatter(y_test, xgb_pred, alpha=0.3, label='XGBoost')
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
    plt.xlabel('Actual ROP')
    plt.ylabel('Predicted ROP')
    plt.title('Actual vs Predicted ROP (USROP)')
    plt.legend()
    plt.savefig('ml_prediction_dir/graphs/usrop_actual_vs_predicted.png')
    plt.close()
    
def train_volve():
    print("\n--- Training on Volve Dataset (Classification) ---")
    df = pd.read_parquet('data/processed/real_training/mud_loss_real_v1.parquet')
    
    target_col = 'is_event'
    features = df.drop(columns=[target_col, 'well_id', 'ddr_activity_phase'], errors='ignore')
    
    # Identify non-numeric columns and encode/drop them if needed. 
    features = features.select_dtypes(include=[np.number])
    
    df_clean = pd.concat([features, df[target_col]], axis=1).dropna()
    X = df_clean.drop(columns=[target_col])
    y = df_clean[target_col]
    
    pos_count = y.sum()
    scale_pos_weight = (len(y) - pos_count) / pos_count if pos_count > 0 else 1
    
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training LightGBM Classifier...")
    lgb_clf = lgb.LGBMClassifier(random_state=42, scale_pos_weight=scale_pos_weight, n_estimators=100)
    lgb_clf.fit(X_train, y_train)
    lgb_pred = lgb_clf.predict(X_test)
    
    print("Training XGBoost Classifier...")
    xgb_clf = xgb.XGBClassifier(random_state=42, scale_pos_weight=scale_pos_weight, n_estimators=100)
    xgb_clf.fit(X_train, y_train)
    xgb_pred = xgb_clf.predict(X_test)
    
    # Safe metric calc
    def get_metrics(y_true, y_pred, model, is_xgb=False):
        try:
            if is_xgb:
                # XGBoost predict_proba structure handling
                prob = model.predict_proba(X_test)
                prob = prob[:, 1] if prob.shape[1] > 1 else prob
            else:
                prob = model.predict_proba(X_test)[:, 1]
            auc = roc_auc_score(y_true, prob)
        except Exception as e:
            auc = np.nan
        return accuracy_score(y_true, y_pred), f1_score(y_true, y_pred, zero_division=0), auc
        
    lgb_acc, lgb_f1, lgb_auc = get_metrics(y_test, lgb_pred, lgb_clf)
    xgb_acc, xgb_f1, xgb_auc = get_metrics(y_test, xgb_pred, xgb_clf, is_xgb=True)
    
    metrics = {
        'Model': ['LightGBM', 'XGBoost'],
        'Accuracy': [lgb_acc, xgb_acc],
        'F1_Score': [lgb_f1, xgb_f1],
        'ROC_AUC': [lgb_auc, xgb_auc]
    }
    
    metrics_df = pd.DataFrame(metrics)
    metrics_df.to_csv('ml_prediction_dir/metrics/volve_metrics.csv', index=False)
    print(metrics_df.to_string(index=False))
    
    # Save the models
    joblib.dump(lgb_clf, 'ml_prediction_dir/saved_models/volve_lgbm.joblib')
    joblib.dump(xgb_clf, 'ml_prediction_dir/saved_models/volve_xgb.joblib')
    
    # Save feature names for FastAPI payload validation
    joblib.dump(list(X.columns), 'ml_prediction_dir/saved_models/volve_features.joblib')
    
    plot_feature_importance(lgb_clf, 'LightGBM Feature Importance (Volve)', 'ml_prediction_dir/graphs/volve_lgbm_importance.png')
    plot_feature_importance(xgb_clf, 'XGBoost Feature Importance (Volve)', 'ml_prediction_dir/graphs/volve_xgb_importance.png')
    
    # Confusion Matrices
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    sns.heatmap(confusion_matrix(y_test, lgb_pred), annot=True, fmt='d', ax=axes[0], cmap='Blues')
    axes[0].set_title('LightGBM Confusion Matrix')
    axes[0].set_xlabel('Predicted')
    axes[0].set_ylabel('Actual')
    
    sns.heatmap(confusion_matrix(y_test, xgb_pred), annot=True, fmt='d', ax=axes[1], cmap='Blues')
    axes[1].set_title('XGBoost Confusion Matrix')
    axes[1].set_xlabel('Predicted')
    axes[1].set_ylabel('Actual')
    
    plt.tight_layout()
    plt.savefig('ml_prediction_dir/graphs/volve_confusion_matrices.png')
    plt.close()

if __name__ == '__main__':
    train_usrop()
    train_volve()
