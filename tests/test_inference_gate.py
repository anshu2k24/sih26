import pytest
import pandas as pd
import numpy as np
from ertmac.ml.inference import DataQualityGate, ShadowInferenceRunner

def test_data_quality_gate_pass():
    gate = DataQualityGate(required_history_md=25.0)
    
    # Create valid history
    mds = np.linspace(100.0, 150.0, 50)
    df = pd.DataFrame({
        'wellbore_id': ['w1'] * 50,
        'md': mds,
        'rop': np.random.rand(50),
        'wob': np.random.rand(50),
        'rpm': np.random.rand(50),
        'torque': np.random.rand(50),
        'hookload': np.random.rand(50),
        'spp': np.random.rand(50),
        'flow_in': np.random.rand(50),
        'mud_density': np.random.rand(50)
    })
    
    status = gate.check_quality(df, current_md=150.0, wellbore_id='w1')
    assert status == "PASS"

def test_data_quality_insufficient_history():
    gate = DataQualityGate(required_history_md=25.0)
    
    # History is only 10m
    mds = np.linspace(140.0, 150.0, 10)
    df = pd.DataFrame({
        'wellbore_id': ['w1'] * 10,
        'md': mds,
        'rop': np.random.rand(10),
        'wob': np.random.rand(10),
        'rpm': np.random.rand(10),
        'torque': np.random.rand(10),
        'hookload': np.random.rand(10),
        'spp': np.random.rand(10),
        'flow_in': np.random.rand(10),
        'mud_density': np.random.rand(10)
    })
    
    status = gate.check_quality(df, current_md=150.0, wellbore_id='w1')
    assert status == "FAIL_INSUFFICIENT_HISTORY"

def test_data_quality_future_leakage():
    gate = DataQualityGate(required_history_md=25.0)
    
    # Includes future data > current_md
    mds = np.linspace(100.0, 160.0, 60)
    df = pd.DataFrame({
        'wellbore_id': ['w1'] * 60,
        'md': mds,
        'rop': np.random.rand(60),
        'wob': np.random.rand(60),
        'rpm': np.random.rand(60),
        'torque': np.random.rand(60),
        'hookload': np.random.rand(60),
        'spp': np.random.rand(60),
        'flow_in': np.random.rand(60),
        'mud_density': np.random.rand(60)
    })
    
    status = gate.check_quality(df, current_md=150.0, wellbore_id='w1')
    assert status == "FAIL_FUTURE_ROWS"

def test_data_quality_sentinels():
    gate = DataQualityGate(required_history_md=25.0)
    
    mds = np.linspace(100.0, 150.0, 50)
    df = pd.DataFrame({
        'wellbore_id': ['w1'] * 50,
        'md': mds,
        'rop': np.random.rand(50),
        'wob': np.random.rand(50),
        'rpm': np.random.rand(50),
        'torque': np.random.rand(50),
        'hookload': np.random.rand(50),
        'spp': np.random.rand(50),
        'flow_in': np.random.rand(50),
        'mud_density': np.random.rand(50)
    })
    
    # Inject sentinel
    df.loc[10, 'torque'] = -999.25
    
    status = gate.check_quality(df, current_md=150.0, wellbore_id='w1')
    assert status == "FAIL_SENTINEL_VALUES"

def test_data_quality_mixed_wells():
    gate = DataQualityGate(required_history_md=25.0)
    
    mds = np.linspace(100.0, 150.0, 50)
    df = pd.DataFrame({
        'wellbore_id': ['w1'] * 49 + ['w2'],
        'md': mds,
        'rop': np.random.rand(50),
        'wob': np.random.rand(50),
        'rpm': np.random.rand(50),
        'torque': np.random.rand(50),
        'hookload': np.random.rand(50),
        'spp': np.random.rand(50),
        'flow_in': np.random.rand(50),
        'mud_density': np.random.rand(50)
    })
    
    status = gate.check_quality(df, current_md=150.0, wellbore_id='w1')
    assert status == "FAIL_MIXED_WELLS"

def test_shadow_runner_no_prediction_state():
    runner = ShadowInferenceRunner(model=None)
    
    # Send empty dataframe
    df = pd.DataFrame()
    output = runner.process_stream(df, current_md=150.0, well_id='w1', timestamp="2024-01-01T00:00:00Z")
    
    assert output.alert_state == "NO_PREDICTION"
    assert output.data_quality_status == "FAIL_EMPTY_HISTORY"
    assert output.risk_score is None

def test_shadow_runner_feature_payload():
    runner = ShadowInferenceRunner(model=None)
    
    mds = np.linspace(100.0, 150.0, 50)
    df = pd.DataFrame({
        'wellbore_id': ['w1'] * 50,
        'md': mds,
        'rop': np.random.rand(50),
        'wob': np.random.rand(50),
        'rpm': np.random.rand(50),
        'torque': np.random.rand(50),
        'hookload': np.random.rand(50),
        'spp': np.random.rand(50),
        'flow_in': np.random.rand(50),
        'mud_density': np.random.rand(50)
    })
    
    output = runner.process_stream(df, current_md=150.0, well_id='w1', timestamp="2024-01-01T00:00:00Z")
    
    assert output.alert_state == "SHADOW_FEATURES_ONLY"
    assert output.data_quality_status == "PASS"
    assert len(output.top_contributing_features) > 0 # Feature payload generated
