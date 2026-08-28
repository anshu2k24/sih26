import pandas as pd

def explore():
    path = '/home/bhavshank/code/sih/data/processed/normalized_events.parquet'
    try:
        df = pd.read_parquet(path)
        print("--- normalized_events.parquet ---")
        print("Columns:", list(df.columns))
        print("Total rows:", len(df))
        print("Event types:\n", df['event_type'].value_counts() if 'event_type' in df.columns else 'N/A')
        print("FORMATION_MUD_LOSS count:", len(df[df['event_type'] == 'FORMATION_MUD_LOSS']) if 'event_type' in df.columns else 'N/A')
        if len(df[df['event_type'] == 'FORMATION_MUD_LOSS']) > 0:
            print("First mud loss row:\n", df[df['event_type'] == 'FORMATION_MUD_LOSS'].iloc[0].to_dict())
    except Exception as e:
        print(e)
        
    path = '/home/bhavshank/code/sih/data/processed/events/event_context.parquet'
    try:
        df = pd.read_parquet(path)
        print("\n--- event_context.parquet ---")
        print("Columns:", list(df.columns))
        print("Total rows:", len(df))
    except Exception as e:
        print(e)

if __name__ == '__main__':
    explore()
