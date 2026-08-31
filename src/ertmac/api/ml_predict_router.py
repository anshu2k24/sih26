import os
import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

router = APIRouter(prefix="/api/predict", tags=["ML Predictions"])

usrop_model_path = 'ml_prediction_dir/saved_models/usrop_xgb.joblib'
usrop_features_path = 'ml_prediction_dir/saved_models/usrop_features.joblib'

volve_model_path = 'ml_prediction_dir/saved_models/volve_xgb.joblib'
volve_features_path = 'ml_prediction_dir/saved_models/volve_features.joblib'

@router.post("/usrop")
def predict_usrop(payload: Dict[str, Any]):
    """Predicts Rate of Penetration (ROP) using the USROP dataset XGBoost model."""
    if not os.path.exists(usrop_model_path) or not os.path.exists(usrop_features_path):
        raise HTTPException(status_code=503, detail="USROP model not loaded.")
        
    model = joblib.load(usrop_model_path)
    features = joblib.load(usrop_features_path)
    
    df = pd.DataFrame([payload])
    
    for col in features:
        if col not in df.columns:
            df[col] = 0.0
            
    df = df[features]
    
    prediction = model.predict(df)[0]
    return {"status": "success", "prediction_rop": float(prediction)}

@router.post("/volve")
def predict_volve(payload: Dict[str, Any]):
    """Predicts mud loss event using the Volve dataset XGBoost model."""
    if not os.path.exists(volve_model_path) or not os.path.exists(volve_features_path):
        raise HTTPException(status_code=503, detail="Volve model not loaded.")
        
    model = joblib.load(volve_model_path)
    features = joblib.load(volve_features_path)
    
    df = pd.DataFrame([payload])
    
    for col in features:
        if col not in df.columns:
            df[col] = 0.0
            
    df = df[features]
    
    prediction = model.predict(df)[0]
    
    try:
        prob = model.predict_proba(df)[0]
        prob_positive = float(prob[1]) if len(prob) > 1 else float(prob[0])
    except Exception:
        prob_positive = None

    return {
        "status": "success", 
        "prediction_is_event": int(prediction), 
        "probability": prob_positive
    }
