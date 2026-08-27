import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from ertmac.ml.dataset import generate_deterministic_negatives
from ertmac.ml.features import construct_causal_features, CausalFeatureConfig
from ertmac.ml.pipeline import LOWOExperimentRunner
from ertmac.ml.contracts import MLPipelineConfig
from ertmac.ml.models import PersistenceBaseline

def test_generate_deterministic_negatives():
    df_sensors = pd.DataFrame({
        'wellbore_id': ['WB1'] * 200,
        'md': np.arange(100.0, 300.0, 1.0) # 200 samples
    })
    
    df_events = pd.DataFrame({
        'wellbore_id': ['WB1'],
        'md': [200.0],
        'event_type': ['TARGET']
    })
    
    # Exclusion zone is +/- 50m around 200.0 -> [150.0, 250.0]
    df_neg = generate_deterministic_negatives(df_sensors, df_events, 'TARGET', ratio=5, exclusion_zone_m=50.0)
    
    assert len(df_neg) <= 5 # 1 positive * 5 ratio
    assert not any((df_neg['md'] >= 150.0) & (df_neg['md'] <= 250.0))
    assert 'is_event' in df_neg.columns
    assert (df_neg['is_event'] == 0).all()
    assert len(df_neg) == df_neg['md'].nunique() # No duplicates

def test_causal_cutoff():
    df_sensor = pd.DataFrame({
        'md': [100.0, 110.0, 120.0, 130.0],
        'rop': [10, 20, 30, 40]
    })
    
    config = CausalFeatureConfig(windows=[5.0, 10.0, 25.0])
    
    # Cutoff at 115.0 -> should only see 100 and 110
    feats = construct_causal_features(df_sensor, 115.0, config)
    
    assert feats['rop_current'] == 20.0
    
    # Assert leakage prevention raises if trying to use future data implicitly
    # The function itself ensures it by doing df_past = df[md <= cutoff]
    
    # What if gap is too large? Cutoff at 120, but latest is 110 -> 10m gap > 5m limit
    with pytest.raises(ValueError, match="Sensor gap too large"):
        construct_causal_features(df_sensor[df_sensor['md'] <= 110.0], 120.0, config)

def test_group_disjoint_lowo():
    config = MLPipelineConfig(min_independent_positive_well_groups=2) # override for test
    runner = LOWOExperimentRunner(config)
    
    df_features = pd.DataFrame({
        'well_id': ['A', 'A', 'B', 'B', 'C', 'C'],
        'independent_group': ['Group1', 'Group1', 'Group2', 'Group2', 'Group3', 'Group3'],
        'is_event': [1, 0, 1, 0, 1, 0],
        'feat1': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        'event_episode_id': [None]*6
    })
    
    res = runner.run_experiment(df_features, PersistenceBaseline())
    
    # 3 groups, so 3 folds
    assert len(res['per_fold_results']) == 3
    
    # Check predictions dataframe
    preds = res['predictions']
    assert len(preds) == 6
    assert set(preds['independent_group']) == {'Group1', 'Group2', 'Group3'}
