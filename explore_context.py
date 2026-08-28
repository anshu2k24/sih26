import pandas as pd

def explore_context():
    path = '/home/bhavshank/code/sih/data/processed/events/event_context.parquet'
    df = pd.read_parquet(path)
    loss = df[df['event_type'] == 'FORMATION_MUD_LOSS']
    print(f"Total MUD_LOSS rows in context: {len(loss)}")
    if len(loss) > 0:
        print("Example:\n", loss.iloc[0].to_dict())
        print("\nUnique episodes:", loss['event_episode_id'].nunique())
        print("Unique wells:", loss['well_id'].unique())
        print("Onset MDs:", loss[['well_id', 'onset_md']].drop_duplicates().to_dict('records'))

if __name__ == '__main__':
    explore_context()
