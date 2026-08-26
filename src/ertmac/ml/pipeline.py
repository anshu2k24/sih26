import pandas as pd
import logging
from typing import List, Dict, Any, Tuple
from .contracts import MLPipelineConfig, causal_feature_cutoff
from .validation import check_feature_leakage, validate_causal_contract, check_overlap
from .models import BaseRiskModel

logger = logging.getLogger("ml_pipeline")

class LOWOExperimentRunner:
    """
    Manages Leave-One-Well-Out (LOWO) scientific evaluation.
    """
    def __init__(self, config: MLPipelineConfig):
        self.config = config
        
    def generate_splits(self, df_features: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Generates LOWO train/test splits safely.
        """
        # Ensure well_id exists
        if 'well_id' not in df_features.columns:
            raise ValueError("Dataset missing 'well_id' for LOWO split.")
            
        # Ensure target exists
        if 'target' not in df_features.columns:
            raise ValueError("Dataset missing 'target' column.")
            
        wells = df_features['well_id'].unique()
        positive_wells = df_features[df_features['target'] == 1]['well_id'].unique()
        
        # Hard readiness gate
        self.config.validate_dataset_readiness(len(positive_wells))
        
        splits = []
        for test_well in wells:
            train_df = df_features[df_features['well_id'] != test_well].copy()
            test_df = df_features[df_features['well_id'] == test_well].copy()
            
            # Check overlap
            check_overlap(set(train_df['well_id']), set(test_df['well_id']))
            
            # Zero-positive fold handling
            if train_df['target'].sum() == 0:
                raise ValueError(f"Fold for test well {test_well} has zero positive examples in train set.")
                
            splits.append((train_df, test_df))
            
        return splits

    def run_experiment(self, df_features: pd.DataFrame, model: BaseRiskModel):
        """
        Executes the LOWO experiment.
        """
        # 1. Validation
        check_feature_leakage(df_features)
        
        # 2. Split Generation
        splits = self.generate_splits(df_features)
        
        results = []
        for i, (train_df, test_df) in enumerate(splits):
            logger.info(f"Fold {i}: Train samples={len(train_df)}, Test samples={len(test_df)}")
            
            # 3. Model Training
            # (Blocked until real data arrives, but the interface is here)
            X_train = train_df.drop(columns=['target', 'well_id', 'md'])
            y_train = train_df['target']
            X_test = test_df.drop(columns=['target', 'well_id', 'md'])
            
            model.fit(X_train, y_train)
            probs = model.predict_proba(X_test)
            
            test_df['pred_proba'] = probs
            results.append(test_df)
            
        return pd.concat(results)
