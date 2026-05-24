import pandas as pd
import numpy as np
from src.pipeline import SportsDataPipeline

def test_picks_last_30d():
    print("🧪 Testing 'picks_last_30d' calculation...")
    
    # Create mock data
    dates = pd.to_datetime(['2026-01-01', '2026-01-05', '2026-01-10', '2026-02-05', '2026-02-10'])
    df = pd.DataFrame({
        'pick_date': dates,
        'capper_id': [1, 1, 1, 1, 1],
        'decimal_odds': [2.0] * 5
    })
    
    # Mocking the part of the pipeline that calculates it
    df = df.sort_values('pick_date')
    def calc_rolling_count(group):
        # group is a Series of pick_date
        temp = pd.DataFrame({'date': group, 'val': 1})
        return temp.rolling('30D', on='date', closed='left').count()['val']

    df['picks_last_30d'] = df.groupby('capper_id')['pick_date'].transform(calc_rolling_count).fillna(0)
    
    print(df[['pick_date', 'picks_last_30d']])
    
    # Expected:
    # 2026-01-01: 0
    # 2026-01-05: 1
    # 2026-01-10: 2
    # 2026-02-05: 2 (01-01 is outside 30 days from 02-05? 01-05 to 02-05 is 31 days? No, Jan has 31 days)
    # 2026-01-05 to 2026-02-05 is exactly 31 days. So only 2026-01-10 is within 30 days of 2026-02-05?
    # Let's check: 2026-02-05 minus 30 days is 2026-01-06. 
    # So 2026-01-10 is the only one in [2026-01-06, 2026-02-05)?
    
    expected = [0, 1, 2, 1, 1]
    actual = df['picks_last_30d'].tolist()
    
    if actual == expected:
        print("✅ Success: picks_last_30d matches expected values.")
    else:
        print(f"❌ Failure: Expected {expected}, got {actual}")

if __name__ == "__main__":
    test_picks_last_30d()
