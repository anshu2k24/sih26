# import pandas as pd

# # however you're currently loading df
# print(df.shape)

# for col in df.columns:
#     print(f"\n{'='*60}")
#     print(col)
#     print("dtype:", df[col].dtype)
#     print("sample:")
#     print(df[col].iloc[0])

import pandas as pd
from huggingface_hub import hf_hub_download

path = hf_hub_download(
    repo_id="bengsoon/volve_daily_drilling_report",
    filename="data/all-00000-of-00001.parquet",
    repo_type="dataset",
)

df = pd.read_parquet(path)

print("Shape:", df.shape)
print("\nColumns:")
print(df.columns.tolist())

for col in df.columns:
    print(f"\n{'=' * 70}")
    print(f"COLUMN: {col}")
    print("dtype:", df[col].dtype)
    print("sample:")
    print(df[col].iloc[0])

print("\n" + "=" * 70)
print("Number of unique wells:", df["nameWell"].nunique())
print("\nWells:")
print(df["nameWell"].value_counts())

df = pd.read_parquet("volve_ddr.parquet")