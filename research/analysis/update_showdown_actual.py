import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from pipeline import SportsDataPipeline, FeatureEngineer

def update_showdown():
    print("📈 Fetching actual data for Staking Showdown...")
    pipeline = SportsDataPipeline()
    raw_df = pipeline.fetch_data_cached()
    if raw_df.empty:
        print("❌ Error: No data found.")
        return

    engineer = FeatureEngineer(raw_df)
    df = engineer.process()
    df = df[df['outcome'].isin([0, 1])].sort_values('pick_date')

    # Identify 'Billion Dollar DNA' signals (Quarry Intelligence Core)
    # Filter: 30d ROI > 5% AND odds between 1.1 and 1.5
    dna_mask = (df['roi_30d'] > 0.05) & (df['decimal_odds'] >= 1.1) & (df['decimal_odds'] <= 1.5)
    dna_signals = df[dna_mask].copy()
    
    if len(dna_signals) < 10:
        print(f"⚠️ Warning: Only {len(dna_signals)} DNA signals found. Broadening filter for simulation...")
        dna_mask = (df['roi_30d'] > 0.0) & (df['decimal_odds'] <= 1.7)
        dna_signals = df[dna_mask].copy()

    print(f"📊 Running showdown over {len(dna_signals)} actual historical signals.")

    # 1. Flat Betting (1.0u)
    flat_bank = 100.0
    flat_history = [flat_bank]
    
    # 2. Hybrid Sequence [0.3, 0.66, 1.45, 3.19, 5.0]
    hybrid_bank = 100.0
    hybrid_history = [hybrid_bank]
    sequence = [0.3, 0.66, 1.45, 3.19, 5.0]
    seq_idx = 0
    max_idx = len(sequence) - 1

    for _, row in dna_signals.iterrows():
        outcome = row['outcome']
        odds = row['decimal_odds']
        
        # Flat
        if outcome == 1:
            flat_bank += 1.0 * (odds - 1)
        else:
            flat_bank -= 1.0
        flat_history.append(flat_bank)
        
        # Hybrid
        bet = sequence[seq_idx]
        if outcome == 1:
            hybrid_bank += bet * (odds - 1)
            seq_idx = 0
        else:
            hybrid_bank -= bet
            seq_idx = (seq_idx + 1) if seq_idx < max_idx else 0
        hybrid_history.append(hybrid_bank)

    # Visualization
    plt.figure(figsize=(14, 8))
    plt.plot(flat_history, label=f'Flat Betting (1.0u) | Net: {flat_bank-100:+.1f}u', color='#0047AB', linewidth=2)
    plt.plot(hybrid_history, label=f'Hybrid Recovery ({sequence}) | Net: {hybrid_bank-100:+.1f}u', color='#228B22', alpha=0.9)
    plt.axhline(100, color='black', linestyle='--', alpha=0.5)
    plt.title(f'Quarry Intelligence Production Showdown: Actual Historical Performance (n={len(dna_signals)} signals)')
    plt.xlabel('Cumulative DNA Signals')
    plt.ylabel('Bankroll Units')
    plt.legend()
    plt.grid(True, alpha=0.2)
    plt.savefig('research/staking_showdown_80wr.png', dpi=200, bbox_inches='tight')
    
    print(f"✅ Graphic updated: research/staking_showdown_80wr.png")
    print(f"   - Flat Final: {flat_bank:.2f}u")
    print(f"   - Hybrid Final: {hybrid_bank:.2f}u")

if __name__ == "__main__":
    update_showdown()
