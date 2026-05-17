import os
import pandas as pd
import numpy as np
import sys
import matplotlib.pyplot as plt

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pipeline import SportsDataPipeline, FeatureEngineer

def calculate_streaks(df):
    """Calculates win/loss streaks for each capper at the time of each pick."""
    print("📊 Calculating streaks (Global and Sport-Specific)...")
    
    # Sort by capper and date to process chronologically
    # We must also sort by 'id' to ensure deterministic order for picks on the same day
    df = df.sort_values(['capper_id', 'pick_date', 'id'])
    
    def get_streak_stats(group):
        outcomes = group['outcome'].values
        
        win_streaks = []
        loss_streaks = []
        
        current_win_streak = 0
        current_loss_streak = 0
        
        for i in range(len(outcomes)):
            # Record streak ENTERING the game
            win_streaks.append(current_win_streak)
            loss_streaks.append(current_loss_streak)
            
            # Update for next game
            if outcomes[i] == 1.0:
                current_win_streak += 1
                current_loss_streak = 0
            elif outcomes[i] == 0.0:
                current_loss_streak += 1
                current_win_streak = 0
            # Pushes/NaNs don't change streaks in this model
                
        return pd.DataFrame({
            'win_streak': win_streaks,
            'loss_streak': loss_streaks
        }, index=group.index)

    # Global Streaks
    streaks = df.groupby('capper_id', group_keys=False).apply(get_streak_stats)
    df['win_streak'] = streaks['win_streak']
    df['loss_streak'] = streaks['loss_streak']
    
    # Sport-Specific Streaks
    sport_streaks = df.groupby(['capper_id', 'league_name'], group_keys=False).apply(get_streak_stats)
    df['sport_win_streak'] = sport_streaks['win_streak']
    df['sport_loss_streak'] = sport_streaks['loss_streak']
    
    return df

def audit_streaks():
    print("📋 STARTING DEEP STREAK AUDIT...")
    
    p = SportsDataPipeline()
    # Use cached data to avoid network calls
    df_raw = p.fetch_data_cached()
    
    if df_raw.empty:
        print("❌ Error: No data found in cache.")
        return

    eng = FeatureEngineer(df_raw)
    df = eng.process()
    
    # Filter for settled bets for streak analysis
    df = df[df['outcome'].isin([0, 1])]
    
    df = calculate_streaks(df)
    
    print("\n--- 📈 WIN STREAK ANALYSIS (Global) ---")
    streak_analysis = df.groupby('win_streak').agg({
        'outcome': ['mean', 'count'],
        'profit_units': 'sum'
    })
    streak_analysis.columns = ['win_rate', 'sample_size', 'total_profit']
    streak_analysis['roi'] = streak_analysis['total_profit'] / streak_analysis['sample_size']
    print(streak_analysis.head(10))
    
    print("\n--- 📉 LOSS STREAK ANALYSIS (Global) ---")
    loss_analysis = df.groupby('loss_streak').agg({
        'outcome': ['mean', 'count'],
        'profit_units': 'sum'
    })
    loss_analysis.columns = ['win_rate', 'sample_size', 'total_profit']
    loss_analysis['roi'] = loss_analysis['total_profit'] / loss_analysis['sample_size']
    print(loss_analysis.head(10))

    print("\n--- 🏀 SPORT-SPECIFIC STREAK ANALYSIS (Example: NBA) ---")
    nba = df[df['league_name'] == 'NBA']
    if not nba.empty:
        nba_streak = nba.groupby('sport_win_streak').agg({
            'outcome': ['mean', 'count'],
            'profit_units': 'sum'
        })
        nba_streak.columns = ['win_rate', 'sample_size', 'total_profit']
        nba_streak['roi'] = nba_streak['total_profit'] / nba_streak['sample_size']
        print(nba_streak.head(5))

    # Visualize
    plt.figure(figsize=(12, 6))
    streak_res = streak_analysis.reset_index()
    loss_res = loss_analysis.reset_index()
    plt.plot(streak_res['win_streak'], streak_res['roi'], marker='o', label='Win Streak ROI')
    plt.plot(loss_res['loss_streak'], loss_res['roi'], marker='x', label='Loss Streak ROI')
    plt.axhline(0, color='red', linestyle='--')
    plt.title('Global ROI vs Entering Streak Length')
    plt.ylabel('ROI (Units per Bet)')
    plt.xlabel('Streak Length')
    plt.grid(True, alpha=0.3)
    plt.savefig('research/streak_roi.png')
    print("\n✅ Saved visualization to research/streak_roi.png")
    
    # Correlation with final outcome
    corr_win = df['win_streak'].corr(df['outcome'])
    corr_loss = df['loss_streak'].corr(df['outcome'])
    print(f"\nCorrelation Win Streak vs Outcome: {corr_win:.4f}")
    print(f"Correlation Loss Streak vs Outcome: {corr_loss:.4f}")
    
    # Best Rule-Based Finder
    print("\n🔎 Searching for profitable simple rules...")
    best_rule = None
    best_roi = -99
    
    for s in range(1, 8):
        # Hot Streak rule
        sub = df[df['win_streak'] >= s]
        if len(sub) > 200:
            roi = sub['profit_units'].sum() / len(sub)
            if roi > best_roi:
                best_roi = roi
                best_rule = f"Bet with Capper when Win Streak >= {s}"
                
        # Cold Streak (Fade) rule
        sub = df[df['loss_streak'] >= s]
        if len(sub) > 200:
            roi = -sub['profit_units'].sum() / len(sub) # Fading means we take the opposite profit
            if roi > best_roi:
                best_roi = roi
                best_rule = f"Fade Capper when Loss Streak >= {s}"

    print(f"🏆 Best Simple Rule: {best_rule} (ROI: {best_roi:.2%})")
    
    # Feature Importance Hint
    print("\n💡 Recommendation for Model Integration:")
    if abs(corr_win) > 0.02 or abs(corr_loss) > 0.02:
        print("✅ STREAKS SHOW SIGNIFICANT CORRELATION. Recommendation: Add 'win_streak' and 'sport_win_streak' as features to XGBoost.")
    else:
        print("⚠️ Streaks show weak linear correlation. They might still work as non-linear features in XGBoost, but a pure rule-based system is risky.")

if __name__ == "__main__":
    audit_streaks()
