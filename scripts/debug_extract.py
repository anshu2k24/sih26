import pandas as pd
import numpy as np
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from ertmac.ml.sequence import extract_sequences
from ertmac.ml.normalization import handle_sentinels_and_impossible

syn_dir = REPO_ROOT / "data" / "synthetic"
df_events = pd.read_parquet(syn_dir / "oil_ertmac_events.parquet")
df_sensors = pd.read_parquet(syn_dir / "oil_ertmac_sensors.parquet")
df_events, _ = handle_sentinels_and_impossible(df_events, is_sensor=False)
df_sensors, _ = handle_sentinels_and_impossible(df_sensors, is_sensor=True)

X, y, groups = extract_sequences(df_events, df_sensors, horizon=25.0, seq_length=50)
print(f"Extracted {len(X)} sequences.")
print(f"y: {np.bincount(y)}")
