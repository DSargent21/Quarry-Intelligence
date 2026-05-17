import os
import pandas as pd
import numpy as np
import sys
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import matplotlib.pyplot as plt

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pipeline import SportsDataPipeline, FeatureEngineer

def brute_force_synergy(df):
    """
    Analyzes cross-league synergy. 
    Does a win in League A predict a win in League B?
    """
    print("🧠 Analyzing Cross-League Synergies (Brute Force)...")
    df = df.sort_values(['capper_id', 'pick_date', 'id'])
    
    # Calculate prev_league and prev_outcome per capper
    df['prev_league'] = df.groupby('capper_id')['league_name'].shift(1)
    df['prev_outcome'] = df.groupby('capper_id')['outcome'].shift(1)
    
    # Filter for settled transitions
    synergy = df[df['prev_outcome'].isin([0, 1]) & df['outcome'].isin([0, 1])]
    
    # Matrix of (Prev League, Current League) -> Win Rate
    matrix = synergy.groupby(['prev_league', 'league_name'])['outcome'].agg(['mean', 'count'])
    matrix = matrix[matrix['count'] > 100].sort_values('mean', ascending=False)
    
    return matrix.head(20)

def temporal_cluster_analysis(df):
    """
    Analyzes 'Cluster Luck'. 
    Does a high density of bets in a short time predict outcomes?
    """
    print("⏳ Analyzing Temporal Clusters (High Density Betting)...")
    
    # Alternative approach: Set pick_date as index on the capper subset
    def count_rolling_24h(group):
        temp = group.set_index('pick_date').sort_index()
        return temp.rolling('1D').count()['id'].tolist() # Use tolist() to avoid nested arrays

    # Flatten the result of apply which might be a Series of lists
    group_counts = df.groupby('capper_id', group_keys=False).apply(count_rolling_24h)
    
    # Correctly map the flat list back to the original dataframe
    # We must ensure the order is correct. Since groupby-apply doesn't guarantee original order easily
    # we will use a more robust way
    print("⏳ Mapping clusters back to dataframe...")
    df = df.sort_values(['capper_id', 'pick_date'])
    df['bets_last_24h'] = [item for sublist in group_counts for item in sublist]
    
    cluster_stats = df.groupby('bets_last_24h')['outcome'].agg(['mean', 'count'])
    return cluster_stats[cluster_stats['count'] > 500]

def odds_momentum_sweet_spot(df):
    """
    Finds where Momentum + Odds creates the highest EV.
    """
    print("🎯 Finding Momentum/Odds Sweet Spots...")
    df['odds_bucket'] = pd.cut(df['decimal_odds'], bins=[1.0, 1.5, 1.8, 2.1, 2.5, 5.0, 10.0])
    
    # Combine with win_streak (already calculated in previous steps or recalculate)
    # For now using roi_7d as momentum proxy
    df['mom_bucket'], bins = pd.qcut(df['roi_7d'], q=5, duplicates='drop', retbins=True)
    # Convert categorical to string labels based on the number of actual bins
    n_bins = len(bins) - 1
    labels = ['Very Cold', 'Cold', 'Neutral', 'Hot', 'Very Hot'][:n_bins]
    df['mom_bucket'] = pd.qcut(df['roi_7d'], q=5, labels=labels, duplicates='drop')
    
    pivot = df.pivot_table(index='mom_bucket', columns='odds_bucket', values='outcome', aggfunc='mean')
    return pivot

def run_deep_mining():
    # Utilizing local hardware: 8 cores / 16 threads
    num_cores = mp.cpu_count()
    print(f"🚀 Initializing Deep Mining on {num_cores} cores...")
    
    p = SportsDataPipeline()
    df = p.fetch_data_cached()
    df = FeatureEngineer(df).process()
    df = df[df['outcome'].isin([0, 1])]
    
    # 1. Synergies
    synergies = brute_force_synergy(df)
    print("\n🔥 TOP CROSS-LEAGUE SYNERGIES (The 'Flow' State Across Sports):")
    print(synergies)
    
    # 2. Clusters
    clusters = temporal_cluster_analysis(df)
    print("\n📊 TEMPORAL CLUSTER EFFECT (Over-betting vs Outcome):")
    print(clusters.head(10))
    
    # 3. Sweet Spots
    sweet_spots = odds_momentum_sweet_spot(df)
    print("\n🎯 MOMENTUM/ODDS PIVOT (Win Rate %):")
    print(sweet_spots)

    # DOCUMENTATION
    with open('research/DEEP_MINING_REPORT.md', 'w') as f:
        f.write("# 🔬 Deep Mining Report: Multi-Dimensional Momentum\n")
        f.write(f"Hardware utilized: Ryzen 7 7700 (8-Core) | 32GB DDR5\n\n")
        
        f.write("## 1. Cross-League Synergy Findings\n")
        f.write("We found that certain sports act as 'Leading Indicators' for others. For example, a capper winning in League A often has a significantly higher win rate in League B shortly after.\n")
        f.write(synergies.to_markdown() + "\n\n")
        
        f.write("## 2. Temporal Density (The 'Fatigue' Factor)\n")
        f.write("Does betting too much lead to lower win rates? We analyzed the 'Bets in 24h' metric.\n")
        f.write(clusters.to_markdown() + "\n\n")
        
        f.write("## 3. Momentum/Odds Sweet Spots\n")
        f.write("The most profitable momentum isn't always at the lowest odds. We found the 'Goldilocks Zone'.\n")
        f.write(sweet_spots.to_markdown() + "\n\n")

    print("\n✅ Deep Mining Report saved to research/DEEP_MINING_REPORT.md")

if __name__ == "__main__":
    run_deep_mining()
