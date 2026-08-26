import pandas as pd
from pathlib import Path

df = pd.read_parquet("/home/bhavshank/code/sih/data/raw/volve_ddr.parquet")
print("Columns in DDR:")
print(df.columns.tolist())

# Check for activity and statusInfo
activity_cols = [c for c in df.columns if 'activity' in c.lower()]
status_cols = [c for c in df.columns if 'statusinfo' in c.lower()]
fluid_cols = [c for c in df.columns if 'fluid' in c.lower()]

print("\nActivity cols:", activity_cols)
print("\nStatus cols:", status_cols)
print("\nFluid cols:", fluid_cols)

# Let's inspect the content of the 'activity' and 'statusInfo' if they exist.
# Usually, WITSML XMLs converted to parquet will have nested structures or flattened columns.
# We'll just look at some non-null values.

for c in activity_cols + status_cols:
    non_nulls = df[c].dropna()
    if len(non_nulls) > 0:
        print(f"\nSample of {c}:")
        print(non_nulls.head(3).values)

