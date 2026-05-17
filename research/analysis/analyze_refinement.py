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

    # Quarry Intelligence DNA Pattern (The Failure)
    dna_mask = (df['roi_30d'] > 0.05) & (df['decimal_odds'] >= 1.1) & (df['decimal_odds'] <= 1.5)
    dna_signals = df[dna_mask].copy()
    
    wr_Quarry Intelligence = dna_signals['outcome'].mean()
    avg_odds_Quarry Intelligence = dna_signals['decimal_odds'].mean()
    be_wr_Quarry Intelligence = 1 / avg_odds_Quarry Intelligence
    
    print(f"🔬 DNA Signal Analysis (Quarry Intelligence Logic):")
    print(f"   - Signal Count: {len(dna_signals)}")
    print(f"   - Win Rate: {wr_Quarry Intelligence:.2%}")
    print(f"   - Alpha: {wr_Quarry Intelligence - be_wr_Quarry Intelligence:+.2%}")
    
    # Quarry Intelligence Refinement: Add Momentum Acceleration + Freshness (The Solution)
    # Filter for signals where ROI is increasing and pick is recent
    Quarry Intelligence_mask = dna_mask & (df['roi_7d'] > df['roi_30d']) & (df['vol_7d'] > 2)
    Quarry Intelligence_signals = df[Quarry Intelligence_mask].copy()
    
    if len(Quarry Intelligence_signals) > 0:
        wr_Quarry Intelligence = Quarry Intelligence_signals['outcome'].mean()
        avg_odds_Quarry Intelligence = Quarry Intelligence_signals['decimal_odds'].mean()
        be_wr_Quarry Intelligence = 1 / avg_odds_Quarry Intelligence
        print(f"\n🧠 Quarry Intelligence Refined (Acceleration + Freshness):")
        print(f"   - Signal Count: {len(Quarry Intelligence_signals)}")
        print(f"   - Win Rate: {wr_Quarry Intelligence:.2%}")
        print(f"   - Alpha: {wr_Quarry Intelligence - be_wr_Quarry Intelligence:+.2%}")

if __name__ == "__main__":
    analyze()
