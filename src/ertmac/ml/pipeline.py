import pandas as pd
from typing import Dict, List
from .contracts import MLPipelineConfig
from .models import BaseModel
from .validation import compute_metrics

class LOWOExperimentRunner:
    def __init__(self, config: MLPipelineConfig):
        self.config = config
        
    def run_experiment(self, df_features: pd.DataFrame, model: BaseModel, target_col: str = 'is_event') -> Dict:
        """
        Runs rigorous Leave-One-Well-Out cross-validation.
        df_features must contain: 'well_id', 'independent_group', and target_col
        """
        if 'independent_group' not in df_features.columns:
            raise ValueError("df_features must contain 'independent_group' for scientific LOWO splitting.")
            
        groups = df_features['independent_group'].unique()
        
        # 1. Gate Check
        pos_groups = df_features[df_features[target_col] == 1]['independent_group'].nunique()
        self.config.validate_dataset_readiness(pos_groups)
        
        # 2. LOWO Execution
        feature_cols = [c for c in df_features.columns if c not in ['well_id', 'independent_group', target_col, 'md', 'timestamp', 'event_episode_id']]
        
        results = []
        all_y_true = []
        all_y_prob = []
        all_groups = []
        
        for g in groups:
            train = df_features[df_features['independent_group'] != g]
            test = df_features[df_features['independent_group'] == g]
            
            if len(test) == 0 or len(train) == 0:
                continue
                
            # Check for leakage explicitly
            assert len(set(train['independent_group']).intersection(set(test['independent_group']))) == 0, "Group Leakage!"
            
            # Train
            model.fit(train[feature_cols], train[target_col])
            
            # Predict
            probs = model.predict_proba(test[feature_cols])
            
            all_y_true.extend(test[target_col].values)
            all_y_prob.extend(probs)
            all_groups.extend(test['independent_group'].values)
            
            try:
                metrics = compute_metrics(test[target_col].values, probs)
            except Exception as e:
                # E.g. undefined if no positives in test fold
                metrics = {"error": str(e), "auc": np.nan, "pr_auc": np.nan}
                
            metrics['holdout_group'] = g
            results.append(metrics)
            
        import numpy as np
        try:
            macro_metrics = compute_metrics(np.array(all_y_true), np.array(all_y_prob))
        except Exception as e:
            macro_metrics = {"error": str(e)}
            
        # Explainability
        feature_importances = {}
        if hasattr(model, 'model') and hasattr(model.model, 'feature_importances_'):
            # LightGBM exposes feature_importances_
            importances = model.model.feature_importances_
            feature_importances = dict(zip(feature_cols, importances))
            
        return {
            "per_fold_results": results,
            "macro_metrics": macro_metrics,
            "predictions": pd.DataFrame({
                "independent_group": all_groups,
                "y_true": all_y_true,
                "y_prob": all_y_prob
            }),
            "feature_importances": feature_importances
        }
