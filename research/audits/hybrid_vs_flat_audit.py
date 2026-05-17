import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from Kyanite_grade_sniper import MasterSniperKyanite

def run_audit():
    print("🔬 Starting Hybrid vs. Flat Betting Audit...")
    sniper = MasterSniperKyanite()
    df = sniper.fetch_and_prepare()
    if df.empty:
        print("❌ Error: No data found.")
        return

    # Train model to get signals
    results = sniper.train(df)
    
    # We need the test data and probabilities
    n_rows = len(df)
    cal_idx = int(n_rows * 0.90)
    test_df = df.iloc[cal_idx:].copy()
    
    test_probs = sniper.model.predict(sniper.xgb.DMatrix(test_df[sniper.features]))
    signals_mask = test_probs >= sniper.conformal_threshold
    active_test = test_df[signals_mask].copy().sort_values('pick_date')

    # 1. Flat Betting (1.0u)
    flat_pnl = np.where(active_test['outcome'] == 1, 1.0 * (active_test['decimal_odds'] - 1), -1.0)
    flat_curve = 100.0 + np.cumsum(flat_pnl)

    # 2. Hybrid Recovery Staking [0.3, 0.66, 1.45, 3.19, 5.0]
    sequence = [0.3, 0.66, 1.45, 3.19, 5.0]
    hybrid_curve = [100.0]
    seq_idx = 0
    current_bank = 100.0
    
    for _, row in active_test.iterrows():
        bet = sequence[seq_idx]
        if row['outcome'] == 1:
            profit = bet * (row['decimal_odds'] - 1)
            current_bank += profit
            seq_idx = 0
        else:
            current_bank -= bet
            seq_idx = (seq_idx + 1) if seq_idx < len(sequence)-1 else 0
        hybrid_curve.append(current_bank)

    # 3. Visualization
    plt.figure(figsize=(12, 7))
    plt.plot(flat_curve, label=f'Flat Betting (1.0u) | Net: {flat_curve[-1]-100:.1f}u', color='blue', alpha=0.8)
    plt.plot(hybrid_curve, label=f'Hybrid Recovery ({sequence}) | Net: {hybrid_curve[-1]-100:.1f}u', color='green', linewidth=2)
    plt.axhline(100, color='black', linestyle='--', alpha=0.5)
    plt.title('Quarry Intelligence Strategy Audit: Flat Betting vs. Optimized Hybrid Staking')
    plt.xlabel('Number of Trades')
    plt.ylabel('Bankroll (Units)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig('research/hybrid_vs_flat_comparison.png', dpi=150)
    
    print(f"✅ Audit Complete.")
    print(f"   - Flat Final: {flat_curve[-1]:.2f}u")
    print(f"   - Hybrid Final: {hybrid_curve[-1]:.2f}u")
    
    if hybrid_curve[-1] > flat_curve[-1]:
        print("🏆 Decision: HYBRID is superior for Quarry Intelligence signals.")
    else:
        print("🏆 Decision: FLAT is superior for Quarry Intelligence signals.")

if __name__ == "__main__":
    # Mocking xgb for the imports inside Kyanite if needed
    import xgboost as xgb
    run_audit()
