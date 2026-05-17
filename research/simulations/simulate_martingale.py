import os
import pandas as pd
import numpy as np
import sys
import matplotlib.pyplot as plt

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pipeline import SportsDataPipeline, FeatureEngineer

def simulate_martingale(df, initial_bankroll=10000, base_bet=100, max_bet=5000, name="Martingale"):
    """
    Simulates a Martingale system on a chronological sequence of bets.
    Enforces bankroll and max bet limits.
    """
    print(f"\n🎲 Simulating {name}: Start=${initial_bankroll}, Base=${base_bet}, MaxBet=${max_bet}")
    
    bankroll = initial_bankroll
    current_bet = base_bet
    history = []
    
    bankrupt_count = 0
    max_drawdown = 0
    peak_bankroll = initial_bankroll
    
    for i, row in df.iterrows():
        if bankroll <= 0:
            history.append(0)
            continue
            
        # Check if we can afford the bet
        if bankroll < current_bet:
            # Forced to bet remaining bankroll
            current_bet = bankroll
            
        # Place the bet
        outcome = row['outcome']
        odds = row['decimal_odds']
        
        # Track for drawdown
        peak_bankroll = max(peak_bankroll, bankroll)
        
        if outcome == 1.0: # WIN
            profit = current_bet * (odds - 1)
            bankroll += profit
            current_bet = base_bet # Reset
        elif outcome == 0.0: # LOSS
            bankroll -= current_bet
            current_bet = min(current_bet * 2, max_bet)
            # If bankroll is zeroed, we stop
            if bankroll <= 0:
                bankroll = 0
        
        history.append(bankroll)
        drawdown = (peak_bankroll - bankroll) / peak_bankroll
        max_drawdown = max(max_drawdown, drawdown)
            
    final_return = (bankroll - initial_bankroll) / initial_bankroll
    print(f"📊 {name} Results:")
    print(f"   • Final Bankroll: ${bankroll:.2f} ({final_return:+.2%})")
    print(f"   • Max Drawdown: {max_drawdown:.2%}")
    print(f"   • Status: {'✅ SURVIVED' if bankroll > 0 else '💀 BANKRUPT'}")
    
    return history

def run_simulations():
    p = SportsDataPipeline()
    df_raw = p.fetch_data_cached()
    eng = FeatureEngineer(df_raw)
    df = eng.process()
    
    # Filter for settled bets and sort chronologically
    df = df[df['outcome'].isin([0, 1])].sort_values('pick_date')
    
    if df.empty:
        print("❌ Error: No data for simulation.")
        return

    plt.figure(figsize=(12, 7))
    
    # 1. Blind Martingale (High Risk)
    # Using a subset of the first 2000 bets to see the behavior clearly
    subset = df.head(2000).copy()
    hist_blind = simulate_martingale(subset, name="Blind Martingale")
    plt.plot(hist_blind, label='Blind Martingale (All Picks)')

    # 2. Selective Martingale (Winning Model Simulation)
    # Let's filter for cappers with > 55% win rate to see if Martingale helps them
    capper_stats = df.groupby('capper_id')['outcome'].mean()
    winning_cappers = capper_stats[capper_stats > 0.55].index
    win_subset = df[df['capper_id'].isin(winning_cappers)].head(2000).copy()
    
    if not win_subset.empty:
        hist_win = simulate_martingale(win_subset, name="Winning-Model Martingale")
        plt.plot(hist_win, label='Winning-Model Martingale (>55% WR)')
    
    # 3. Flat Betting Comparison (Control)
    bankroll = 10000
    flat_hist = []
    for i, row in win_subset.iterrows():
        profit = 100 * (row['decimal_odds'] - 1) if row['outcome'] == 1.0 else -100
        bankroll += profit
        flat_hist.append(bankroll)
    plt.plot(flat_hist, label='Flat Betting (Control)', linestyle='--')

    plt.axhline(10000, color='black', linestyle=':', alpha=0.5)
    plt.title('Martingale System vs Flat Betting (Realistic Constraints)')
    plt.ylabel('Bankroll ($)')
    plt.xlabel('Bet Number')
    plt.legend()
    plt.grid(True, alpha=0.2)
    plt.savefig('research/martingale_results.png')
    print("\n✅ Saved comparison visualization to research/martingale_results.png")

if __name__ == "__main__":
    run_simulations()
