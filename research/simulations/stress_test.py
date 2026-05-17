import os
import pandas as pd
import numpy as np
import sys
import matplotlib.pyplot as plt

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from pipeline import SportsDataPipeline, FeatureEngineer

def run_stress_test():
    print("🛡️ Starting Monte Carlo Stress Test (1,000 Simulations)...")
    
    p = SportsDataPipeline()
    df = p.fetch_data_cached()
    df = FeatureEngineer(df).process()
    df = df[df['outcome'].isin([0, 1])]
    
    # Isolate Momentum Rider Data
    df = df.sort_values(['capper_id', 'pick_date', 'id'])
    df['win_streak'] = df.groupby('capper_id')['outcome'].transform(lambda x: x.shift(1).rolling(100, min_periods=1).apply(lambda y: (y==1).iloc[::-1].cumprod().sum() if len(y)>0 else 0, raw=False)).fillna(0)
    df['mom_delta'] = df['roi_7d'] - (df['roi_30d'] / 4.2)
    rider_df = df[(df['win_streak'] >= 3) & (df['mom_delta'] > 0.5)].copy()
    
    actual_outcomes = rider_df['outcome'].values
    actual_odds = rider_df['decimal_odds'].values
    
    # Optimized Sequence: [0.3, 0.66, 1.45, 3.19, 5.0]
    opt_seq = [0.3, 0.66, 1.45, 3.19, 5.0]
    
    sim_results = []
    ruin_count = 0
    
    plt.figure(figsize=(12, 6))
    
    for s in range(1000):
        # Bootstrap: Shuffle outcomes to simulate "Worst Possible Luck"
        indices = np.random.choice(len(actual_outcomes), size=len(actual_outcomes), replace=True)
        s_outcomes = actual_outcomes[indices]
        s_odds = actual_odds[indices]
        
        bankroll = 100.0
        history = [bankroll]
        seq_idx = 0
        
        for i in range(len(s_outcomes)):
            if bankroll <= 0:
                bankroll = 0
                break
            
            bet = min(opt_seq[seq_idx], bankroll)
            if s_outcomes[i] == 1.0:
                bankroll += bet * (s_odds[i] - 1)
                seq_idx = 0
            else:
                bankroll -= bet
                seq_idx = (seq_idx + 1) if seq_idx < len(opt_seq)-1 else 0
            history.append(bankroll)
            
        if bankroll <= 0: ruin_count += 1
        sim_results.append(bankroll)
        if s < 50: # Plot first 50 paths
            plt.plot(history, color='blue', alpha=0.05)

    plt.axhline(100, color='red', linestyle='--')
    plt.title('Monte Carlo Stress Test: 1,000 "Worst Luck" Scenarios')
    plt.ylabel('Bankroll (Units)')
    plt.xlabel('Trades')
    plt.savefig('research/monte_carlo_stress_test.png')
    
    ruin_rate = (ruin_count / 1000) * 100
    avg_final = np.mean(sim_results)
    
    print(f"✅ Stress Test Complete.")
    print(f"   • Risk of Ruin: {ruin_rate}%")
    print(f"   • Average Final Bankroll: {avg_final:.1f}u")
    
    return ruin_rate, avg_final

if __name__ == "__main__":
    run_stress_test()
