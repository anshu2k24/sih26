import os
import pandas as pd

def explore_usrop():
    data_dir = '/home/bhavshank/code/sih/data/raw/usrop'
    files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    
    total_rows = 0
    well_ids = set()
    columns = None
    depth_ranges = {}
    missing_values = {}
    
    for f in files:
        path = os.path.join(data_dir, f)
        df = pd.read_csv(path)
        
        total_rows += len(df)
        
        if columns is None:
            columns = list(df.columns)
            missing_values = {col: 0 for col in columns}
            missing_values['sentinel_999'] = 0
            
        wells = df['Well Identifier'].unique() if 'Well Identifier' in df.columns else []
        well_ids.update(wells)
        
        if 'Measured Depth m' in df.columns:
            for w in wells:
                w_df = df[df['Well Identifier'] == w]
                min_md = w_df['Measured Depth m'].min()
                max_md = w_df['Measured Depth m'].max()
                depth_ranges[w] = f"{min_md:.2f} - {max_md:.2f}"
                
        for col in columns:
            if col in df.columns:
                missing_values[col] += df[col].isna().sum()
                if df[col].dtype in ['float64', 'int64']:
                    missing_values['sentinel_999'] += (df[col] == -999.0).sum() + (df[col] == -999.25).sum()
                
    print("USROP DATA")
    print("Files:", files)
    print("Total rows:", total_rows)
    print("Columns:", columns)
    print("Wells:", well_ids)
    print("Depth ranges:", depth_ranges)
    print("Missing/Sentinel:", missing_values)

def explore_ddr():
    path = '/home/bhavshank/code/sih/data/raw/volve_ddr.parquet'
    if os.path.exists(path):
        df = pd.read_parquet(path)
        print("\nDDR DATA")
        print("Rows:", len(df))
        print("Columns:", list(df.columns))
        print("Event types:", df['DDR_OPERATION'].unique() if 'DDR_OPERATION' in df.columns else 'N/A')
        
if __name__ == '__main__':
    explore_usrop()
    explore_ddr()
