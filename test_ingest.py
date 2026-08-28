import os
import sys
from pathlib import Path

# Add src to path so we can import ertmac
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from ertmac.ml.normalization import ingest_file

def explore_ddr_with_norm():
    p = Path('/home/bhavshank/code/sih/data/raw/volve_ddr.parquet')
    df, invalid = ingest_file(p, is_event=True)
    print("DDR Parsed Columns:", df.columns.tolist())
    print("Total rows:", len(df))
    print("Event types:\n", df['event_type'].value_counts())
    
    # Check for FORMATION_MUD_LOSS
    loss_events = df[df['event_type'] == 'FORMATION_MUD_LOSS']
    print(f"MUD_LOSS count: {len(loss_events)}")
    if len(loss_events) > 0:
        print("Example:\n", loss_events.iloc[0].to_dict())
        
if __name__ == '__main__':
    explore_ddr_with_norm()
