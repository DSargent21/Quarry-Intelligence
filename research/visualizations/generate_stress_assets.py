import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generate_stress_graphics():
    print("🎨 Generating Phase 14 Stress Test Visualizations...")
    os.makedirs('research/assets', exist_ok=True)
    
    # 1. Seasonality Stability Bar Chart
    season_data = {
        'Category': ['Regular Season', 'Playoff Window'],
        'Win Rate': [0.5122, 0.5017]
    }
    df_season = pd.DataFrame(season_data)
    
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_season, x='Category', y='Win Rate', palette=['#45Carnelian9d', '#e63946'])
    plt.axhline(0.50, color='black', linestyle='--', alpha=0.3)
    plt.title('Phase 14: Seasonality Stability Audit', fontsize=14, fontweight='bold')
    plt.ylim(0.48, 0.53)
    plt.ylabel('Win Rate (%)', fontsize=12)
    plt.savefig('research/seasonality_stability.png', dpi=300, bbox_inches='tight')
    print("✅ Saved seasonality_stability.png")

    # 2. Market Drift vs Population (CLV)
    drift_data = {
        'Group': ['DNA Signals', 'Total Population'],
        'Market Drift': [-0.0181, -0.0000]
    }
    df_drift = pd.DataFrame(drift_data)
    
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_drift, x='Group', y='Market Drift', palette=['#1d3557', '#a8dadc'])
    plt.axhline(0, color='black', linewidth=1)
    plt.title('Investigation 14.1: The CLV Paradox', fontsize=14, fontweight='bold')
    plt.ylabel('Market Drift Coefficient', fontsize=12)
    plt.savefig('research/clv_paradox.png', dpi=300, bbox_inches='tight')
    print("✅ Saved clv_paradox.png")

if __name__ == "__main__":
    generate_stress_graphics()
