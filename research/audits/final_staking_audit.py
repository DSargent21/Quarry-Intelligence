import os
import pandas as pd
import numpy as np
import sys
import matplotlib.pyplot as plt

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pipeline import SportsDataPipeline, FeatureEngineer

def run_final_comparison():
    print("🚀 Running Final Staking System Comparison: Hybrid Recovery vs Flat Betting...")
    
    p = SportsDataPipeline()
    df = p.fetch_data_cached()
    df = FeatureEngineer(df).process()
    df = df[df['outcome'].isin([0, 1])].sort_values('pick_date')
    
    # 1. FLAT BETTING (1.0u per bet)
    bankroll_flat = 1000
    history_flat = []
    for i, row in df.iterrows():
        profit = 1.0 * (row['decimal_odds'] - 1) if row['outcome'] == 1.0 else -1.0
        bankroll_flat += profit
        history_flat.append(bankroll_flat)
        
    # 2. HYBRID RECOVERY (0.2 -> 2.0 sequence)
    sequence = [0.2, 0.4, 0.5, 0.7, 1.0, 1.5, 2.0]
    bankroll_hybrid = 1000
    seq_idx = 0
    history_hybrid = []
    for i, row in df.iterrows():
        current_bet = sequence[seq_idx]
        if row['outcome'] == 1.0:
            bankroll_hybrid += current_bet * (row['decimal_odds'] - 1)
            seq_idx = 0
        else:
            bankroll_hybrid -= current_bet
            seq_idx = (seq_idx + 1) if (seq_idx + 1) < len(sequence) else 0
        history_hybrid.append(bankroll_hybrid)

    # VISUALIZATION
    plt.figure(figsize=(15, 8))
    plt.plot(history_flat, label=f'Flat Betting (1.0u) | Final: {bankroll_flat:.2f}u', color='blue', alpha=0.7)
    plt.plot(history_hybrid, label=f'Hybrid Recovery (0.2-2.0u) | Final: {bankroll_hybrid:.2f}u', color='orange', linewidth=2)
    
    plt.axhline(1000, color='red', linestyle='--', alpha=0.5)
    plt.title('Institutional Audit: Flat Betting vs. Hybrid Recovery (All 130k+ Trades)')
    plt.ylabel('Bankroll (Units)')
    plt.xlabel('Cumulative Bets')
    plt.legend()
    plt.grid(True, alpha=0.2)
    plt.savefig('research/staking_comparison.png')
    
    print(f"✅ Comparison Complete. Flat: {bankroll_flat:.2f}u | Hybrid: {bankroll_hybrid:.2f}u")
    print("✅ Visualization saved to research/staking_comparison.png")

if __name__ == "__main__":
    run_final_comparison()
