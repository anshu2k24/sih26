import pytest
import os
import pandas as pd
from ertmac.ml.inference import load_production_model, ModelSafetyError

def test_real_only_dataset():
    df = pd.read_parquet('data/processed/events/volve_real_only_ml.parquet')
    assert 'synthetic' not in df['source'].unique()
    assert (df['source'] == 'real_event').sum() == 3
    assert df['source'].nunique() <= 2 # real_event and real_negative

def test_model_loading_and_rejection():
    # should succeed
    model = load_production_model('models/volve_research_v1.joblib')
    assert model is not None
    
    # should reject
    with pytest.raises(ModelSafetyError):
        load_production_model('models/ertmac_production_v1.joblib')

def test_trace_generated():
    trace = pd.read_csv('reports/ml/volve_replay_prediction_trace.csv')
    assert len(trace) > 0
    assert 'risk_score' in trace.columns
    assert 'actual_label' in trace.columns
