import pandas as pd

try:
    usrop_df = pd.read_parquet('data/processed/usrop/usrop_clean.parquet')
    volve_df = pd.read_parquet('data/processed/real_training/mud_loss_real_v1.parquet')
    
    usrop_cols = set(usrop_df.columns)
    volve_cols = set(volve_df.columns)
    
    common = usrop_cols.intersection(volve_cols)
    print("Common columns count:", len(common))
    print("Common columns:", common)
    print("USROP target 'MudLoss' values:", usrop_df['MudLoss'].value_counts().to_dict() if 'MudLoss' in usrop_df.columns else "N/A")
    print("Volve target 'is_event' values:", volve_df['is_event'].value_counts().to_dict() if 'is_event' in volve_df.columns else "N/A")

except Exception as e:
    print("Error:", e)

