import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generate_quantum_graphics():
    print("🎨 Generating Quantum Momentum Visualizations...")
    os.makedirs('research/assets', exist_ok=True)
    
    # 1. Investigation B: Momentum Friction/Acceleration Bar Chart
    friction_data = {
        'League': ['NBA', 'NFL', 'MLB', 'NHL', 'NCAAB', 'NCAAF'],
        'WR@1': [0.5480, 0.5155, 0.5040, 0.5536, 0.5390, 0.5312],
        'WR@3': [0.5552, 0.5418, 0.5377, 0.5586, 0.5185, 0.5775]
    }
    df_friction = pd.DataFrame(friction_data)
    df_melted = df_friction.melt(id_vars='League', var_name='Streak', value_name='Win Rate')
    
    plt.figure(figsize=(12, 6))
    sns.barplot(data=df_melted, x='League', y='Win Rate', hue='Streak', palette=['#a8dadc', '#e63946'])
    plt.axhline(0.50, color='black', linestyle='--', alpha=0.3)
    plt.title('Momentum Friction vs. Acceleration (WR@1 vs WR@3)', fontsize=14, fontweight='bold')
    plt.ylabel('Win Rate (%)', fontsize=12)
    plt.ylim(0.45, 0.60)
    plt.legend(title='Streak Depth')
    plt.savefig('research/momentum_friction.png', dpi=300, bbox_inches='tight')
    print("✅ Saved momentum_friction.png")

    # 2. Investigation A: Survivor League Distribution (Donut Chart)
    survivor_leagues = {
        'League': ['MLB', 'NCAAB', 'NBA', 'NHL', 'NCAAF', 'Other'],
        'Share': [0.219, 0.207, 0.202, 0.100, 0.096, 0.176]
    }
    df_surv = pd.DataFrame(survivor_leagues)
    
    plt.figure(figsize=(8, 8))
    colors = sns.color_palette('rocket', n_colors=6)
    plt.pie(df_surv['Share'], labels=df_surv['League'], autopct='%1.1f%%', startangle=140, colors=colors, pctdistance=0.85)
    centre_circle = plt.Circle((0,0), 0.70, fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    plt.title('Investigation A: Survivor League Concentration', fontsize=14, fontweight='bold')
    plt.savefig('research/survivor_leagues.png', dpi=300, bbox_inches='tight')
    print("✅ Saved survivor_leagues.png")

    # 3. Investigation C: Smart Money Synergy Matrix
    synergy_data = [
        [0.547, 0.557, 0.536], # HOT State
        [0.499, 0.499, 0.497]  # OTHER State
    ]
    drift_labels = ['Negative Drift', 'Stable Market', 'Positive Drift']
    state_labels = ['HOT Capper', 'Other Capper']
    df_synergy = pd.DataFrame(synergy_data, index=state_labels, columns=drift_labels)
    
    plt.figure(figsize=(10, 6))
    sns.heatmap(df_synergy, annot=True, cmap='RdYlGn', fmt='.3f', cbar=True)
    plt.title('Investigation C: The "Clear Path" Synergy Matrix', fontsize=14, fontweight='bold')
    plt.xlabel('Market Drift (Smart Money)', fontsize=12)
    plt.ylabel('Capper State', fontsize=12)
    plt.savefig('research/smart_money_synergy.png', dpi=300, bbox_inches='tight')
    print("✅ Saved smart_money_synergy.png")

if __name__ == "__main__":
    generate_quantum_graphics()
