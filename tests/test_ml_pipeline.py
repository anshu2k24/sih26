import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from ertmac.ml.contracts import MLPipelineConfig, causal_feature_cutoff
from ertmac.ml.validation import check_feature_leakage, validate_causal_contract, check_overlap
from ertmac.ml.pipeline import LOWOExperimentRunner
from ertmac.ml.features import CausalFeatureConfig, construct_causal_features
from ertmac.ml.models import LogisticRegressionBaseline

def test_schema_and_cutoff():
    onset_md = 3000.0
    cutoff = causal_feature_cutoff(onset_md, 25.0)
    assert cutoff == 2975.0

def test_leakage_detection():
    df = pd.DataFrame({'rop': [10, 20], 'mitigation_used': [1, 0]})
    with pytest.raises(ValueError, match="CRITICAL LEAKAGE DETECTED"):
        check_feature_leakage(df)

def test_overlap_integrity():
    with pytest.raises(ValueError, match="LOWO INTEGRITY VIOLATION"):
        check_overlap({'WellA', 'WellB'}, {'WellB', 'WellC'})

def test_readiness_gate():
    config = MLPipelineConfig(min_independent_positive_well_groups=5)
    with pytest.raises(ValueError, match="ML BLOCKED"):
        config.validate_dataset_readiness(3)
        
def test_zero_positive_fold_handling():
    config = MLPipelineConfig(min_independent_positive_well_groups=1)
    runner = LOWOExperimentRunner(config)
    # create fake dataset where one fold leaves 0 positives in train
    df = pd.DataFrame({
        'independent_group': ['WellA', 'WellB', 'WellC'],
        'target': [1, 0, 0],
        'md': [100, 200, 300],
        'rop': [10, 20, 30]
    })
    # the fit method of LogisticRegressionBaseline will throw ValueError if only one class in y
    # but the runner itself will execute it. Let's test that the runner fails gracefully or we can just test the exception.
    with pytest.raises(ValueError):
        runner.run_experiment(df, LogisticRegressionBaseline(), 'target')

def test_feature_construction():
    config = CausalFeatureConfig(windows=[10.0], sensor_channels=['rop'])
    df_sensor = pd.DataFrame({
        'md': [2960.0, 2965.0, 2970.0, 2975.0, 2980.0],
        'rop': [10, 15, 20, 25, 30]
    })
    
    feats = construct_causal_features(df_sensor, 2975.0, config)
    
    assert feats['rop_current'] == 25.0
    assert feats['rop_mean_10.0m'] == 20.0
    assert feats['rop_max_10.0m'] == 25.0
    assert feats['rop_delta_10.0m'] == 10.0 # 25 - 15

def test_ml_blocked_exception():
    config = MLPipelineConfig(min_independent_positive_well_groups=5)
    runner = LOWOExperimentRunner(config)
    model = LogisticRegressionBaseline()
    
    df = pd.DataFrame({
        'independent_group': ['WellA', 'WellB'],
        'target': [1, 1],
        'rop': [10, 20]
    })
    with pytest.raises(ValueError, match="ML BLOCKED"):
        runner.run_experiment(df, model, 'target')
