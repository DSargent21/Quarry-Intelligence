import os
import pandas as pd
import numpy as np
import sys
import matplotlib.pyplot as plt
from datetime import timedelta

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pipeline import SportsDataPipeline, FeatureEngineer

def calculate_physics_metrics(df):
    """
    Deeper Momentum Analysis:
    - Momentum Half-Life (Temporal decay of a hot streak)
    - State Transition Matrix (Markov Chain)
    - Velocity (Bets per day during streak)
    """
    print("🧬 Analyzing Momentum Physics...")
    df = df.sort_values(['capper_id', 'pick_date', 'id'])
    
    # 1. State Labeling
    def label_state(row):
        if row['win_streak'] >= 3: return 'HOT'
        if row['loss_streak'] >= 3: return 'COLD'
        return 'NEUTRAL'
    
    # We need win_streak/loss_streak from audit_streaks logic
    # Re-calculating briefly for standalone integrity
    def get_streaks(group):
        outcomes = group['outcome'].values
        win_streaks, loss_streaks = [], []
        curr_w, curr_l = 0, 0
        for o in outcomes:
            win_streaks.append(curr_w)
            loss_streaks.append(curr_l)
            if o == 1: curr_w += 1; curr_l = 0
            else: curr_l += 1; curr_w = 0
        return pd.DataFrame({'win_streak': win_streaks, 'loss_streak': loss_streaks}, index=group.index)

    streaks = df.groupby('capper_id', group_keys=False).apply(get_streaks)
    df['win_streak'] = streaks['win_streak']
    df['loss_streak'] = streaks['loss_streak']
    df['state'] = df.apply(label_state, axis=1)
    df['next_state'] = df.groupby('capper_id')['state'].shift(-1)
    
    # 2. Transition Matrix (Markov Chain)
    print("📊 Calculating State Transition Probabilities (The Gravity of Slumps)...")
    transitions = df.groupby(['state', 'next_state']).size().unstack(fill_value=0)
    transition_probs = transitions.div(transitions.sum(axis=1), axis=0)
    
    # 3. Momentum Half-Life (Temporal Decay)
    print("⏱️ Calculating Momentum Half-Life (Decay of 'Hot' state)...")
    # Identify chunks of 'HOT' state
    df['state_change'] = df['state'] != df.groupby('capper_id')['state'].shift(1)
    df['streak_id'] = df.groupby('capper_id')['state_change'].cumsum()
    
    hot_streaks = df[df['state'] == 'HOT'].copy()
    if not hot_streaks.empty:
        # Time since start of hot streak
        hot_streaks['streak_start'] = hot_streaks.groupby(['capper_id', 'streak_id'])['pick_date'].transform('min')
        hot_streaks['days_in_hot'] = (hot_streaks['pick_date'] - hot_streaks['streak_start']).dt.total_seconds() / 86400
        
        # Win rate decay over days in hot state
        decay = hot_streaks.groupby(hot_streaks['days_in_hot'].round()).agg({'outcome': ['mean', 'count']})
        decay.columns = ['win_rate', 'count']
        decay = decay[decay['count'] > 50]
    else:
        decay = pd.DataFrame()

    # 4. Momentum Velocity (Density of wins)
    print("🚀 Analyzing Momentum Velocity (Bets per Day during streaks)...")
    df = df.sort_values(['capper_id', 'pick_date', 'id'])
    
    velocities = []
    for capper_id, group in df.groupby('capper_id'):
        temp = group.set_index('pick_date').sort_index()
        vel = temp['id'].rolling('7D', closed='left').count().fillna(0).values
        velocities.extend(vel)
    
    df['bets_prev_7d'] = velocities
    
    velocity_impact = df.groupby(pd.cut(df['bets_prev_7d'], bins=[0, 5, 15, 30, 100])).agg({
        'outcome': ['mean', 'count']
    })
    velocity_impact.columns = ['win_rate', 'count']

    return transition_probs, decay, velocity_impact

def run_physics_audit():
    p = SportsDataPipeline()
    df_raw = p.fetch_data_cached()
    eng = FeatureEngineer(df_raw)
    df = eng.process()
    df = df[df['outcome'].isin([0, 1])]
    
    transitions, decay, velocity = calculate_physics_metrics(df)
    
    print("\n--- 🌌 TRANSITION PROBABILITIES (Markov Matrix) ---")
    print(transitions)
    
    print("\n--- 📉 MOMENTUM DECAY (Win Rate over time in 'HOT' state) ---")
    print(decay.head(10))
    
    print("\n--- 🏎️ VELOCITY IMPACT (Bet Density vs Win Rate) ---")
    print(velocity)

    # Export Report Bits
    with open('research/MOMENTUM_PHYSICS.md', 'w') as f:
        f.write("# 🧪 Deep Momentum Physics: The Wave Mechanics of Winning\n\n")
        f.write("## 1. State Transition Matrix (Markovian Gravity)\n")
        f.write("Probabilities of moving between Hot, Neutral, and Cold states.\n\n")
        f.write(transitions.to_markdown() + "\n\n")
        
        f.write("## 2. Momentum Half-Life (Temporal Decay)\n")
        f.write("How win rates degrade as a 'HOT' streak persists over time.\n\n")
        f.write(decay.to_markdown() + "\n\n")
        
        f.write("## 3. Momentum Velocity (Density Impact)\n")
        f.write("Higher density (Velocity) often leads to faster burnout.\n\n")
        f.write(velocity.to_markdown() + "\n\n")

    print("\n✅ Deep Research complete. Report generated at research/MOMENTUM_PHYSICS.md")

if __name__ == "__main__":
    run_physics_audit()
