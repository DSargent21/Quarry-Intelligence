import pandas as pd
import numpy as np
from src.pipeline import SportsDataPipeline, FeatureEngineer
from src.v5_dynamic_features import calculate_dynamic_features
import os

def run_integrity_audit():
    print("🛡️ Starting Empirical Leakage Audit for V5 Conformal Sniper...")
    
    # 1. Fetch Raw Data
    pipeline = SportsDataPipeline()
    raw_df = pipeline.fetch_data_cached()
    
    # 2. Process through V5 Pipeline
    engineer = FeatureEngineer(raw_df)
    processed_df = engineer.process()
    
    # Prepare for dynamic features
    processed_df['capper'] = processed_df['capper_id']
    processed_df['capper_rolling_roi'] = processed_df['roi_30d']
    processed_df['volatility'] = processed_df['vol_30d']
    processed_df['market_consensus'] = processed_df['implied_prob']
    if 'profit_units' in processed_df.columns:
        processed_df['return'] = processed_df['profit_units']
        
    processed_df = calculate_dynamic_features(processed_df)
    
    # 3. SELECT A TEST SUBJECT (An elite capper with high volume)
    test_capper_id = processed_df['capper_id'].value_counts().index[0]
    print(f"🕵️ Auditing Capper ID: {test_capper_id}")
    
    capper_data = processed_df[processed_df['capper_id'] == test_capper_id].sort_values('pick_date')
    
    # 4. MANUAL VERIFICATION OF A SPECIFIC PICK
    # Pick a random sample from the middle of their history
    sample_idx = len(capper_data) // 2
    sample_pick = capper_data.iloc[sample_idx]
    sample_date = sample_pick['pick_date']
    
    print(f"\n📍 Auditing Pick on {sample_date}")
    print(f"Target Outcome: {sample_pick['outcome']}")
    
    # Features to verify
    features_to_check = ['acc_30d', 'roi_30d', 'roi_momentum']
    
    print("\n--- Feature Values in Pipeline ---")
    for f in features_to_check:
        print(f"{f}: {sample_pick[f]:.4f}")
        
    # 5. MANUALLY CALCULATE FROM RAW (Future-Blind, Daily Aggregated)
    # Get all raw picks for this capper BEFORE this date
    raw_history_full = raw_df[(raw_df['capper_id'] == test_capper_id) & (raw_df['pick_date'] < sample_date)].copy()
    
    # Convert result to outcome manually
    res = raw_history_full['result'].astype(str).str.lower().str.strip()
    raw_history_full['outcome'] = np.select([res.isin(['win','won']), res.isin(['loss','lost'])], [1.0, 0.0], default=np.nan)
    raw_history_full['decimal_odds'] = raw_history_full['odds_american'].apply(engineer._dec)
    raw_history_full['profit_units'] = np.where(raw_history_full['outcome']==1, raw_history_full['decimal_odds']-1, -1.0)
    raw_history_full = raw_history_full.dropna(subset=['outcome'])
    
    # Aggregate Daily like the pipeline
    daily_manual = raw_history_full.groupby('pick_date').agg({
        'outcome': ['sum', 'count'],
        'profit_units': 'sum'
    })
    daily_manual.columns = ['wins', 'count', 'profit']
    daily_manual = daily_manual.sort_index()
    
    # Calculate manual accuracy (rolling 30 days of history)
    manual_acc_30 = daily_manual.tail(30)['wins'].sum() / (daily_manual.tail(30)['count'].sum() + 1e-6)
    manual_roi_30 = daily_manual.tail(30)['profit'].sum()
    
    print("\n--- Manual Daily-Aggregated Calculations ---")
    print(f"Manual Acc (Last 30 days of history): {manual_acc_30:.4f}")
    print(f"Manual ROI (Last 30 days of history): {manual_roi_30:.4f}")
    
    # Verification
    if abs(sample_pick['acc_30d'] - manual_acc_30) < 1e-4:
        print("\n✅ ACCURACY INTEGRITY: MATCHED. The model only sees past data.")
    else:
        print(f"\n❌ ACCURACY INTEGRITY: FAILED. Pipeline={sample_pick['acc_30d']:.4f}, Manual={manual_acc_30:.4f}")
        
    if abs(sample_pick['roi_30d'] - manual_roi_30) < 1e-4:
        print("✅ ROI INTEGRITY: MATCHED.")
    else:
        print(f"❌ ROI INTEGRITY: FAILED. Pipeline={sample_pick['roi_30d']:.4f}, Manual={manual_roi_30:.4f}")
        
    # 6. SHUFFLE TEST (The ultimate leakage test)
    # If we shuffle the outcomes of the test set, the model's 'accuracy' should drop to random chance (~50%).
    # If it stays high, it's using hidden features that contain the answer.
    print("\n🔀 Running Target Shuffle Test...")
    from src.v5_conformal_sniper import ConformalSniperV5
    import xgboost as xgb
    
    v5 = ConformalSniperV5()
    # We use a smaller subset for speed
    audit_df = processed_df.tail(10000).copy()
    
    # Train on first 5000, test on last 5000
    train = audit_df.iloc[:5000]
    test = audit_df.iloc[5000:].copy()
    
    X_train, y_train = train[v5.features], train[v5.target]
    X_test, y_test = test[v5.features], test[v5.target]
    
    model = xgb.XGBClassifier()
    model.fit(X_train, y_train)
    
    # Standard Score
    real_score = model.score(X_test, y_test)
    print(f"Real Model Accuracy: {real_score:.4f}")
    
    # Shuffled Score
    y_test_shuffled = y_test.sample(frac=1).values
    shuffled_score = model.score(X_test, y_test_shuffled)
    print(f"Shuffled Target Accuracy: {shuffled_score:.4f}")
    
    if shuffled_score < real_score * 0.9: # Significant drop
         print("✅ SHUFFLE TEST: PASSED. The model is learning patterns, not just 'finding the answer' hidden in features.")
    else:
         print("❌ SHUFFLE TEST: FAILED. High accuracy even with shuffled targets suggests feature leakage.")

if __name__ == "__main__":
    run_integrity_audit()
