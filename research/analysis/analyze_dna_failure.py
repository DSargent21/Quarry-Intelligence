import pandas as pd
import numpy as np
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from pipeline import SportsDataPipeline, FeatureEngineer

def analyze():
    pipeline = SportsDataPipeline()
    raw_df = pipeline.fetch_data_cached()
    engineer = FeatureEngineer(raw_df)
    df = engineer.process()
    df = df[df['outcome'].isin([0, 1])]

    # Quarry Intelligence DNA Pattern
    dna_mask = (df['roi_30d'] > 0.05) & (df['decimal_odds'] >= 1.1) & (df['decimal_odds'] <= 1.5)
    dna_signals = df[dna_mask].copy()
    
    wr = dna_signals['outcome'].mean()
    avg_odds = dna_signals['decimal_odds'].mean()
    be_wr = 1 / avg_odds
    
    print(f"🔬 DNA Signal Analysis (Quarry Intelligence Logic):")
    print(f"   - Signal Count: {len(dna_signals)}")
    print(f"   - Realized Win Rate: {wr:.2%}")
    print(f"   - Average Odds: {avg_odds:.3f}")
    print(f"   - Breakeven Win Rate Required: {be_wr:.2%}")
    print(f"   - Alpha (WR - BE_WR): {wr - be_wr:+.2%}")
    
    # Check Quarry Intelligence Refining: Fatigue
    dna_signals['is_fatigued'] = (dna_signals['bets_last_24h'] > 13).astype(int)
    Quarry Intelligence_signals = dna_signals[dna_signals['is_fatigued'] == 0].copy()
    
    Quarry Intelligence_wr = Quarry Intelligence_signals['outcome'].mean()
    print(f"\n🧠 Quarry Intelligence Refined (No Fatigue):")
    print(f"   - Signal Count: {len(Quarry Intelligence_signals)}")
    print(f"   - Realized Win Rate: {Quarry Intelligence_wr:.2%}")
    print(f"   - Alpha (WR - BE_WR): {Quarry Intelligence_wr - be_wr:+.2%}")

if __name__ == "__main__":
    analyze()
