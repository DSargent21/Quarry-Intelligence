import os
import pandas as pd
import numpy as np
import sys
import json
import xgboost as xgb
import matplotlib.pyplot as plt

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pipeline import SportsDataPipeline, FeatureEngineer
from models import calculate_dynamic_features

def run_zenith_backtest():
    print("🚀 INITIALIZING ZENITH EDGE BACKTEST...")
    p = SportsDataPipeline()
    raw = p.fetch_data_cached()
    eng = FeatureEngineer(raw)
    df = eng.process()
    
    # Prep features
    df['capper'] = df['capper_id']
    df['capper_rolling_roi'] = df['roi_30d']
    df['volatility'] = df['vol_30d']
    df['market_consensus'] = df['implied_prob']
    df['return'] = df['profit_units']
    df = calculate_dynamic_features(df)
    
    # Zenith Specific Features
    daily_counts = df.groupby(['capper_id', 'pick_date']).size().reset_index(name='daily_count')
    daily_counts['pick_date'] = daily_counts['pick_date'] + pd.Timedelta(days=1)
    df = df.merge(daily_counts.rename(columns={'daily_count': 'bets_last_24h'}), on=['capper_id', 'pick_date'], how='left')
    df['bets_last_24h'] = df['bets_last_24h'].fillna(0)
    df['synergy_score'] = 0.5
    df['is_dna_pattern'] = ((df['roi_7d'] > 0.05) & (df['vol_7d'] < 0.2)).astype(int)
    
    # Load Kyanite
    booster = xgb.Booster()
    booster.load_model('models/kyanite.json')
    
    with open('models/kyanite_config.json', 'r') as f:
        config = json.load(f)
    feats = config['features']
    
    dtest = xgb.DMatrix(df[feats])
    df['raw_prob'] = booster.predict(dtest)
    df['raw_edge'] = df['raw_prob'] - df['implied_prob']
    
    # Filter for active tracking period (to keep it relevant)
    df = df[df['pick_date'] >= '2025-11-01'].copy()
    
    print("\n📊 PROFILE 1: KYANITE (THE MARKETABLE SNIPER)")
    print("Goal: Maximize Win Rate (Retail Appeal) while staying +EV.")
    # Standard: 0.65 Certainty / 2% Edge
    cand_k = df[(df['raw_prob'] >= 0.65) & (df['raw_edge'] >= 0.02)].copy()
    cand_k = cand_k.sort_values(['pick_date', 'raw_prob'], ascending=[True, False]).drop_duplicates(subset=['pick_date', 'pick_norm'], keep='first')
    
    if not cand_k.empty:
        roi_k = (cand_k['profit_units'].sum() / cand_k['unit'].sum()) * 100
        wr_k = (len(cand_k[cand_k['outcome'] == 1]) / len(cand_k)) * 100
        print(f"Kyanite Status -> Picks: {len(cand_k)} | WR: {wr_k:.1f}% | ROI: {roi_k:+.2f}%")

    print("\n📊 PROFILE 2: CARNELIAN (THE BAYESIAN VALUE ENGINE)")
    print("Goal: Maximize Bayesian +EV (Edge) regardless of win rate.")
    # Standard: 0.45 Certainty / 6% Edge
    cand_c = df[(df['raw_prob'] >= 0.45) & (df['raw_edge'] >= 0.06)].copy()
    cand_c = cand_c.sort_values(['pick_date', 'raw_edge'], ascending=[True, False]).drop_duplicates(subset=['pick_date', 'pick_norm'], keep='first')
    
    if not cand_c.empty:
        roi_c = (cand_c['profit_units'].sum() / cand_c['unit'].sum()) * 100
        wr_c = (len(cand_c[cand_c['outcome'] == 1]) / len(cand_c)) * 100
        print(f"Carnelian Status -> Picks: {len(cand_c)} | WR: {wr_c:.1f}% | ROI: {roi_c:+.2f}%")

    # Save to report
    with open('research/DEEP_MINING_REPORT.md', 'a') as f:
        f.write("\n## 6. Strategic Realignment: Marketable vs. Bayesian Value\n")
        f.write("We have formally split the Zenith architecture into two distinct operational profiles:\n\n")
        f.write("- **Kyanite (Marketable Sniper):** Targets heavy favorites (>0.65 Certainty) to provide a high-frequency win profile for retail environments.\n")
        f.write("- **Carnelian (Bayesian Value Engine):** Targets absolute edge (>6.0%) regardless of win probability, maximizing institutional yield through value-underdog capture.\n")

if __name__ == "__main__":
    run_zenith_backtest()
