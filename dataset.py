# import pandas as pd
# from huggingface_hub import hf_hub_download

# path = hf_hub_download(
#     repo_id="bengsoon/volve_daily_drilling_report",
#     filename="data/all-00000-of-00001.parquet",
#     repo_type="dataset",
# )
# df = pd.read_parquet(path)
# print(df.shape)
# print(df.columns.tolist())

import pandas as pd
from huggingface_hub import hf_hub_download

path = hf_hub_download(
    repo_id="bengsoon/volve_daily_drilling_report",
    filename="data/all-00000-of-00001.parquet",
    repo_type="dataset",
)

df = pd.read_parquet(path)

print(df.shape)
print(df.columns.tolist())

# Save locally
df.to_parquet("volve_ddr.parquet", index=False)

print("\nSaved as: volve_ddr.parquet")