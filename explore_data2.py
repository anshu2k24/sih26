import os
import pandas as pd
import json

def explore_usrop():
    data_dir = '/home/bhavshank/code/sih/data/raw/usrop'
    files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    
    total_rows = 0
    depth_ranges = {}
    
    for f in files:
        path = os.path.join(data_dir, f)
        df = pd.read_csv(path)
        
        total_rows += len(df)
        
        if 'Measured Depth m' in df.columns:
            min_md = df['Measured Depth m'].min()
            max_md = df['Measured Depth m'].max()
            depth_ranges[f] = f"{min_md:.2f} - {max_md:.2f}"
            
    print("Depth ranges:", json.dumps(depth_ranges, indent=2))
    
    # Just grab an example row
    path = os.path.join(data_dir, files[0])
    df = pd.read_csv(path)
    print("Example Row:\n", df.iloc[0].to_dict())

def explore_ddr():
    path = '/home/bhavshank/code/sih/data/raw/volve_ddr.parquet'
    if os.path.exists(path):
        df = pd.read_parquet(path)
        print("\nDDR DATA")
        # filter by FORMATION_MUD_LOSS ? Wait, the event type is in 'dTimStart' or 'activity' or 'lithShowInfo'?
        print("Columns:", list(df.columns))
        if 'activity' in df.columns:
            print("Activity unique:", df['activity'].unique()[:10])

if __name__ == '__main__':
    explore_usrop()
    explore_ddr()
