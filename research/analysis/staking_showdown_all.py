import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# Path setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, 'src'))

from Kyanite_grade_sniper import MasterSniperKyanite

def run_simulation(outcomes, odds, n_trades):
    initial_bankroll = 100.0
    
    # 1. Flat Betting (1.0u)
    flat_bank = initial_bankroll
    flat_history = [flat_bank]
    
    # 2. Hybrid Sequence [0.3, 0.66, 1.45, 3.19, 5.0]
    hybrid_bank = initial_bankroll
    hybrid_history = [hybrid_bank]
    sequence = [0.3, 0.66, 1.45, 3.19, 5.0]
    seq_idx = 0
    
    for i in range(len(outcomes)):
        res = outcomes[i]
        odd = odds[i]
        
        # Flat logic
        if res == 1:
            flat_bank += 1.0 * (odd - 1)
        else:
            flat_bank -= 1.0
        flat_history.append(flat_bank)
        
        # Hybrid logic
        bet = sequence[seq_idx]
        if res == 1:
            hybrid_bank += bet * (odd - 1)
            seq_idx = 0
        else:
            hybrid_bank -= bet
            seq_idx = min(seq_idx + 1, len(sequence) - 1)
        hybrid_history.append(hybrid_bank)
        
    return flat_history, hybrid_history

def main():
    print("🔬 Loading data from cache...")
    sniper = MasterSniperKyanite()
    df = sniper.fetch_and_prepare()
    if df.empty:
        print("❌ Error: No data found.")
        return

    # Train model to get signals (using training/calibration/test split)
    # We want to identify the DNA signals in the FULL dataset for the most robust comparison
    # But to be fair, we should use the model's identified signals in the test/validation set
    
    print("🧠 Training Kyanite model...")
    sniper.train(df)
    
    # Get all signals from the entire dataset using the calibrated threshold
    import xgboost as xgb
    dall = xgb.DMatrix(df[sniper.features])
    probs = sniper.model.predict(dall)
    mask = probs >= sniper.conformal_threshold
    
    active_df = df[mask].copy().sort_values('pick_date')
    outcomes = active_df['outcome'].values
    odds = active_df['decimal_odds'].values
    n_signals = len(active_df)
    
    print(f"📊 Identified {n_signals} signals above threshold {sniper.conformal_threshold:.4f}")
    
    flat, hybrid = run_simulation(outcomes, odds, n_signals)
    
    plt.figure(figsize=(12, 7))
    plt.plot(flat, label=f'Flat Betting (1.0u) | Net: {flat[-1]-100:+.1f}u', color='blue', alpha=0.9)
    plt.plot(hybrid, label=f'Hybrid Recovery (0.3-5.0u) | Net: {hybrid[-1]-100:+.1f}u', color='green', linewidth=2)
    plt.axhline(100, color='black', linestyle='--', alpha=0.5)
    plt.title(f'Quarry Intelligence Universal Showdown (n={n_signals} Total Research Picks)')
    plt.xlabel('Trades')
    plt.ylabel('Bankroll Units')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig('research/staking_showdown_all.png', dpi=200)
    print(f"✅ Comparison chart saved to research/staking_showdown_all.png")

if __name__ == "__main__":
    main()
