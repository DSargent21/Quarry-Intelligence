import pandas as pd
import os

cache_path = 'data/picks_cache.parquet'
if os.path.exists(cache_path):
    df = pd.read_parquet(cache_path)
    print(f"Total rows: {len(df)}")
    print(f"Date range: {df['pick_date'].min()} to {df['pick_date'].max()}")
    print("\nRecent results distribution:")
    if 'result' in df.columns:
        print(df[df['pick_date'] >= '2026-05-15']['result'].value_counts())
    else:
        print("Column 'result' missing")
    
    print("\nSample of most recent rows:")
    cols = ['pick_date', 'pick_value', 'result', 'canonical_name']
    available_cols = [c for c in cols if c in df.columns]
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(df[available_cols].tail(20))
else:
    print("Cache not found")
