import pytest
import os
import pandas as pd
from sklearn.model_selection import LeaveOneGroupOut
from ertmac.ml.inference import load_production_model, ModelSafetyError

def test_contaminated_model_rejected():
    with pytest.raises(ModelSafetyError, match="INVALID MODEL.*quarantined due to synthetic contamination"):
        load_production_model('models/ertmac_production_v1.joblib')

def test_synthetic_model_rejected():
    with pytest.raises(ModelSafetyError, match="Synthetic models cannot be used in production"):
        load_production_model('models/synthetic_cnn_v1.joblib')

def test_real_only_dataset_no_synthetic():
    events = pd.read_csv('reports/tables/verified_event_episodes_v2.csv')
    assert 'synthetic' not in events['onset_confidence'].unique()
    assert 'synthetic' not in events['event_type'].unique()
    
def test_lowo_disjoint_groups():
    logo = LeaveOneGroupOut()
    df = pd.DataFrame({'x': [1,2,3,4], 'y': [0,1,0,1], 'group': ['A', 'A', 'B', 'B']})
    for train_idx, test_idx in logo.split(df[['x']], df['y'], df['group']):
        train_groups = set(df.iloc[train_idx]['group'])
        test_groups = set(df.iloc[test_idx]['group'])
        assert train_groups.isdisjoint(test_groups)
