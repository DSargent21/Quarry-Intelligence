import os
import pandas as pd
import numpy as np
import sys
import matplotlib.pyplot as plt

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from pipeline import SportsDataPipeline, FeatureEngineer

def simulate_flat(outcomes, odds, unit=1.0, start_bank=100.0):
    bankroll = start_bank
    history = [bankroll]
    for i in range(len(outcomes)):
        profit = unit * (odds[i] - 1) if outcomes[i] == 1.0 else -unit
        bankroll += profit
        history.append(bankroll)
    return history

def simulate_martingale(outcomes, odds, base_bet=0.1, max_bet=5.0, start_bank=100.0):
    bankroll = start_bank
    current_bet = base_bet
    history = [bankroll]
    for i in range(len(outcomes)):
        if bankroll <= 0:
            history.append(0)
            continue
        
        bet = min(current_bet, bankroll, max_bet)
        if outcomes[i] == 1.0:
            bankroll += bet * (odds[i] - 1)
            current_bet = base_bet
        else:
            bankroll -= bet
            current_bet *= 2.0
            
        history.append(bankroll)
    return history

def simulate_hybrid(outcomes, odds, sequence, start_bank=100.0):
    bankroll = start_bank
    seq_idx = 0
    history = [bankroll]
    for i in range(len(outcomes)):
        if bankroll <= 0:
            history.append(0)
            continue
            
        bet = min(sequence[seq_idx], bankroll)
        if outcomes[i] == 1.0:
            bankroll += bet * (odds[i] - 1)
            seq_idx = 0
        else:
            bankroll -= bet
            seq_idx = (seq_idx + 1) if seq_idx < len(sequence)-1 else 0
            
        history.append(bankroll)
    return history

def run_standardized_audit():
    print("🚀 Running Standardized Audit (100u Bankroll, Triple Benchmark)...")
    
    p = SportsDataPipeline()
    df = p.fetch_data_cached()
    df = FeatureEngineer(df).process()
    df = df[df['outcome'].isin([0, 1])]
    
    # Pre-calculate momentum features for the "Momentum Rider" subset
    df = df.sort_values(['capper_id', 'pick_date', 'id'])
    df['win_streak'] = df.groupby('capper_id')['outcome'].transform(lambda x: x.shift(1).rolling(100, min_periods=1).apply(lambda y: (y==1).iloc[::-1].cumprod().sum() if len(y)>0 else 0, raw=False)).fillna(0)
    df['mom_delta'] = df['roi_7d'] - (df['roi_30d'] / 4.2)
    
    # Subset: Momentum Rider (The Winning Trend)
    rider_df = df[(df['win_streak'] >= 3) & (df['mom_delta'] > 0.5)].copy()
    outcomes = rider_df['outcome'].values
    odds = rider_df['decimal_odds'].values
    
    # 1. FLAT BENCHMARK
    hist_flat = simulate_flat(outcomes, odds)
    
    # 2. MARTINGALE BENCHMARK (0.1u base, 5u cap)
    hist_mart = simulate_martingale(outcomes, odds)
    
    # 3. HYBRID RECOVERY (Optimized: [0.3, 0.66, 1.45, 3.19, 5.0])
    opt_seq = [0.3, 0.66, 1.45, 3.19, 5.0]
    hist_hyb = simulate_hybrid(outcomes, odds, opt_seq)
    
    # VISUALIZATION 1: EQUITY CURVES
    plt.figure(figsize=(15, 8))
    plt.plot(hist_flat, label=f'Flat Betting (1u) | Final: {hist_flat[-1]:.1f}u', color='grey', linestyle='--', alpha=0.7)
    plt.plot(hist_mart, label=f'Classic Martingale (0.1u Base) | Final: {hist_mart[-1]:.1f}u', color='red', alpha=0.6)
    plt.plot(hist_hyb, label=f'Optimized Hybrid (0.3u Base) | Final: {hist_hyb[-1]:.1f}u', color='green', linewidth=2.5)
    
    plt.axhline(100, color='black', linewidth=1)
    plt.title('Momentum Rider: Performance Benchmark (Starting Bankroll: 100.0u)')
    plt.ylabel('Bankroll (Units)')
    plt.xlabel('Number of Trades')
    plt.legend()
    plt.grid(True, alpha=0.2)
    plt.savefig('research/standardized_performance.png')
    
    # VISUALIZATION 2: DRAWDOWN VS RETURN (Bar Chart)
    labels = ['Flat', 'Martingale', 'Hybrid']
    returns = [hist_flat[-1]-100, hist_mart[-1]-100, hist_hyb[-1]-100]
    
    def get_max_dd(hist):
        peak = np.maximum.accumulate(hist)
        peak[peak == 0] = 1 # Avoid div by zero
        dd = (peak - hist) / peak
        return np.max(dd) * 100
        
    dds = [get_max_dd(hist_flat), get_max_dd(hist_mart), get_max_dd(hist_hyb)]
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twinx()
    
    ax1.bar(labels, returns, color='skyblue', label='Net Profit (u)', alpha=0.7)
    ax2.plot(labels, dds, color='red', marker='D', label='Max Drawdown (%)', linewidth=2)
    
    ax1.set_ylabel('Net Profit (Units)')
    ax2.set_ylabel('Max Drawdown (%)')
    plt.title('Risk vs Reward: Staking System Comparison (100u Base)')
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    plt.grid(True, axis='y', alpha=0.2)
    plt.savefig('research/risk_reward_comparison.png')

    print(f"✅ Audit Complete. Final Bankrolls: Flat={hist_flat[-1]:.1f}u, Mart={hist_mart[-1]:.1f}u, Hyb={hist_hyb[-1]:.1f}u")

if __name__ == "__main__":
    run_standardized_audit()
