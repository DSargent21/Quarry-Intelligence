import pandas as pd
import numpy as np
import os
import sys

# Path setup
BASE_DIR = os.getcwd()
sys.path.append(os.path.join(BASE_DIR, 'src'))

from pipeline import SportsDataPipeline, FeatureEngineer

def debug_features():
    print("🚀 Starting Feature Debug...")
    pipeline = SportsDataPipeline()
    raw_df = pipeline.fetch_data_cached()
    
    if raw_df.empty:
        print("❌ Data is empty!")
        return

    print(f"📊 Data Range: {raw_df['pick_date'].min()} to {raw_df['pick_date'].max()}")
    
    fe = FeatureEngineer(raw_df)
    df = fe.process()
    
    feat_cols = ['roi_30d', 'acc_30d', 'vol_30d', 'v4_consensus_count_lag1']
    print("\nFeature Statistics (All Data):")
    print(df[feat_cols].describe())
    
    print("\nMissing/Zero features per day (last 10 days):")
    last_dates = sorted(df['pick_date'].unique())[-10:]
    for d in last_dates:
        day_df = df[df['pick_date'] == d]
        zeros = (day_df['roi_30d'] == 0).sum()
        total = len(day_df)
        print(f"{pd.to_datetime(d).date()}: {zeros}/{total} picks have roi_30d == 0 ({zeros/total:.1%})")

    # Check a specific capper's features
    top_capper = df['capper_id'].value_counts().index[0]
    print(f"\nDebug for Top Capper {top_capper}:")
    capper_df = df[df['capper_id'] == top_capper].sort_values('pick_date')
    print(capper_df[['pick_date', 'roi_30d', 'acc_30d']].tail(10))

if __name__ == "__main__":
    debug_features()
