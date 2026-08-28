import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score, recall_score, f1_score
from pathlib import Path

# load model
model = joblib.load('models/ertmac_production_v1.joblib')

# Let's inspect the model object to see its parameters
print("Model Pipeline:", model)

# Try to find the dataset used for training to answer the lineage questions.
if hasattr(model, 'classes_'):
    print("Classes:", model.classes_)
