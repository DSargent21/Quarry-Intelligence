import os
import pandas as pd
import numpy as np
import sys
import matplotlib.pyplot as plt

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pipeline import SportsDataPipeline, FeatureEngineer

def run_quantum_investigations():
    print("🚀 Initializing Quantum Momentum Investigations...")
    p = SportsDataPipeline()
    df_raw = p.fetch_data_cached()
    eng = FeatureEngineer(df_raw)
    df = eng.process()
    df = df[df['outcome'].isin([0, 1])]
    
    # Pre-requisite: Recalculate streaks
    df = df.sort_values(['capper_id', 'pick_date', 'id'])
    def get_streaks(group):
        outcomes = group['outcome'].values
        win_streaks, loss_streaks = [], []
        curr_w, curr_l = 0, 0
        for o in outcomes:
            win_streaks.append(curr_w); loss_streaks.append(curr_l)
            if o == 1: curr_w += 1; curr_l = 0
            else: curr_l += 1; curr_w = 0
        return pd.DataFrame({'win_streak': win_streaks, 'loss_streak': loss_streaks}, index=group.index)

    streaks = df.groupby('capper_id', group_keys=False).apply(get_streaks)
    df['win_streak'] = streaks['win_streak']
    
    # --- INVESTIGATION A: SECOND WIND (SURVIVORSHIP) ---
    print("🔬 Auditing Investigation A: The Second Wind...")
    survivors = df[df['win_streak'] >= 5].copy()
    if not survivors.empty:
        # Comparison: Survivors vs Broader Population
        avg_odds_surv = survivors['decimal_odds'].mean()
        avg_odds_pop = df['decimal_odds'].mean()
        
        # League concentration of survivors
        league_conc = survivors['league_name'].value_counts(normalize=True).head(5)
        
        print(f"   - Survivor Avg Odds: {avg_odds_surv:.2f} (Pop: {avg_odds_pop:.2f})")
        print(f"   - Survivor League Concentration:\n{league_conc}")
    
    # --- INVESTIGATION B: CROSS-SPORT FRICTION ---
    print("🔬 Auditing Investigation B: Cross-Sport Friction...")
    leagues = ['NBA', 'NFL', 'MLB', 'NHL', 'NCAAB', 'NCAAF']
    friction_results = {}
    
    for league in leagues:
        league_df = df[df['league_name'] == league].copy()
        if len(league_df) > 500:
            # Re-calculate streak for THIS league only
            def get_l_streaks(group):
                outcomes = group['outcome'].values
                ws = []
                cw = 0
                for o in outcomes:
                    ws.append(cw)
                    if o == 1: cw += 1
                    else: cw = 0
                return pd.Series(ws, index=group.index)
            
            league_df['l_win_streak'] = league_df.groupby('capper_id', group_keys=False).apply(get_l_streaks)
            
            # Win Rate at Streak 1 vs Streak 3 (Persistence)
            wr_1 = league_df[league_df['l_win_streak'] == 1]['outcome'].mean()
            wr_3 = league_df[league_df['l_win_streak'] == 3]['outcome'].mean()
            
            # Friction = Decay rate
            friction = (wr_1 - wr_3) if not pd.isna(wr_3) else 0
            friction_results[league] = {'wr_1': wr_1, 'wr_3': wr_3, 'friction': friction}

    print("   - Friction Coefficients (Lower is better/more storage):")
    for l, res in friction_results.items():
        print(f"     {l}: {res['friction']:.4f} (WR3: {res['wr_3']:.2%})")

    # --- INVESTIGATION C: SMART MONEY SYNERGY ---
    print("🔬 Auditing Investigation C: Smart Money Synergy...")
    # Use market_drift as proxy for Smart Money (Phase 9)
    if 'market_drift' in df.columns:
        # State labeling
        df['state'] = np.where(df['win_streak'] >= 3, 'HOT', 'OTHER')
        
        # Intersection of HOT and Positive Market Drift
        synergy = df.groupby(['state', pd.cut(df['market_drift'], bins=[-1, -0.01, 0.01, 1])])['outcome'].agg(['mean', 'count'])
        print("   - Synergy Matrix (State vs Market Drift):")
        print(synergy)

    # --- GENERATE SUMMARY REPORT ---
    with open('research/QUANTUM_RESULTS.md', 'w') as f:
        f.write("# 🌌 Quantum Momentum Results: Pinpointing the Quarry Intelligence Edge\n\n")
        f.write("## 1. Investigation A: The Second Wind (Day 5 survivors)\n")
        f.write(f"- Survivor Avg Odds: {avg_odds_surv:.2f}\n")
        f.write(f"- Top League: {league_conc.index[0]} ({league_conc.values[0]:.1%})\n\n")
        
        f.write("## 2. Investigation B: Momentum Friction by League\n")
        f.write("| League | WR@1 | WR@3 | Friction |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for l, res in friction_results.items():
            f.write(f"| {l} | {res['wr_1']:.2%} | {res['wr_3']:.2%} | {res['friction']:.4f} |\n")
        
        f.write("\n## 3. Investigation C: Smart Money Alignment\n")
        f.write(synergy.to_markdown() + "\n")

    print("\n✅ Quantum Investigations complete. Results at research/QUANTUM_RESULTS.md")

if __name__ == "__main__":
    run_quantum_investigations()
