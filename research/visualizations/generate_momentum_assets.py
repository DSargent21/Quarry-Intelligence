import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from matplotlib.colors import LinearSegmentedColormap

# Site Aesthetic Constants
VOID = '#020617'
KYANITE = '#0ea5e9'
CARNELIAN = '#f97316'
GRID = '#1A1A1A'
TEXT = '#E2E2E2'
DIM_TEXT = '#666666'

def setup_style():
    plt.style.use('dark_background')
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Inter', 'Space Grotesk', 'DejaVu Sans'],
        'axes.facecolor': VOID,
        'figure.facecolor': VOID,
        'axes.edgecolor': GRID,
        'grid.color': GRID,
        'text.color': TEXT,
        'axes.labelcolor': TEXT,
        'xtick.color': DIM_TEXT,
        'ytick.color': DIM_TEXT,
        'axes.titleweight': 'bold',
        'axes.titlesize': 16,
        'axes.titlepad': 20
    })

def generate_graphics():
    print("🎨 Generating Zenith Institutional Visualizations...")
    os.makedirs('research/assets', exist_ok=True)
    setup_style()
    
    # 1. Momentum Half-Life Decay Plot
    decay_data = {
        'days_in_hot': [0, 1, 2, 3, 4, 5, 6, 7],
        'win_rate': [0.5627, 0.5375, 0.5397, 0.5209, 0.5251, 0.5150, 0.5110, 0.4831] # Smoothed for visual clarity
    }
    df_decay = pd.DataFrame(decay_data)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Glow effect
    for i in range(1, 5):
        sns.lineplot(data=df_decay, x='days_in_hot', y='win_rate', ax=ax, linewidth=2.5 + i*2, color=KYANITE, alpha=0.05)
    
    sns.lineplot(data=df_decay, x='days_in_hot', y='win_rate', ax=ax, marker='o', linewidth=3, color=KYANITE, markersize=8)
    
    ax.axhline(0.50, color='#ffffff', linestyle='--', alpha=0.2, linewidth=1)
    ax.fill_between(df_decay['days_in_hot'], 0.50, df_decay['win_rate'], alpha=0.1, color=KYANITE)
    
    ax.set_title('ALPHA HALF-LIFE: TEMPORAL DECAY CURVE', loc='left')
    ax.set_xlabel('DAYS POST-TRIGGER (HOT STATE)', fontfamily='monospace', fontsize=10, alpha=0.8)
    ax.set_ylabel('WIN RATE (%)', fontfamily='monospace', fontsize=10, alpha=0.8)
    
    ax.set_ylim(0.45, 0.60)
    ax.grid(True, linestyle=':', alpha=0.3)
    
    plt.savefig('research/momentum_decay.png', dpi=300, bbox_inches='tight', pad_inches=0.2)
    print("✅ Saved momentum_decay.png")

    # 2. Transition Gravity Heatmap
    matrix_data = [
        [0.546, 0.000, 0.454],
        [0.000, 0.556, 0.444],
        [0.088, 0.092, 0.820]
    ]
    states = ['COLD', 'HOT', 'NEUTRAL']
    df_matrix = pd.DataFrame(matrix_data, index=states, columns=states)
    
    # Custom Gradient: VOID -> KYANITE -> CARNELIAN
    cmap = LinearSegmentedColormap.from_list('quarry', [VOID, KYANITE, CARNELIAN], N=256)
    
    plt.figure(figsize=(9, 7))
    sns.heatmap(df_matrix, annot=True, cmap=cmap, fmt='.3f', cbar=False, 
                annot_kws={"size": 14, "weight": "bold", "family": "monospace"},
                linewidths=1, linecolor=GRID)
    
    plt.title('MARKOVIAN GRAVITY: STATE TRANSITION MATRIX', loc='left')
    plt.xlabel('NEXT STATE (T+1)', fontfamily='monospace', fontsize=10, alpha=0.8)
    plt.ylabel('CURRENT STATE (T)', fontfamily='monospace', fontsize=10, alpha=0.8)
    
    plt.savefig('research/transition_gravity.png', dpi=300, bbox_inches='tight', pad_inches=0.2)
    print("✅ Saved transition_gravity.png")

    # 3. Strategic Performance Matrix (Radar/Spider Chart)
    labels = np.array(['WIN RATE', 'ROI', 'LIQUIDITY', 'CAPACITY', 'SHARPE'])
    kyanite_vals = np.array([0.842, 0.121, 0.40, 0.35, 0.95])
    carnelian_vals = np.array([0.540, 0.061, 0.95, 0.90, 0.78])
    
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    
    # Close the loop
    kyanite_vals = np.concatenate((kyanite_vals, [kyanite_vals[0]]))
    carnelian_vals = np.concatenate((carnelian_vals, [carnelian_vals[0]]))
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    
    # Grid styling
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(0)
    
    plt.xticks(angles[:-1], labels, fontfamily='monospace', fontsize=10, fontweight='bold')
    plt.yticks([0.2, 0.4, 0.6, 0.8, 1.0], ["20%", "40%", "60%", "80%", "100%"], color=DIM_TEXT, size=8)
    plt.ylim(0, 1.1)
    
    # Plot Kyanite
    ax.plot(angles, kyanite_vals, color=KYANITE, linewidth=3, label='KYANITE (PRECISION)')
    ax.fill(angles, kyanite_vals, color=KYANITE, alpha=0.2)
    
    # Plot Carnelian
    ax.plot(angles, carnelian_vals, color=CARNELIAN, linewidth=3, label='CARNELIAN (CAPACITY)')
    ax.fill(angles, carnelian_vals, color=CARNELIAN, alpha=0.2)
    
    ax.set_title('INSTITUTIONAL PERFORMANCE MATRIX', pad=30)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), frameon=False, 
               prop={'family': 'monospace', 'size': 9})
    
    plt.savefig('research/performance_matrix.png', dpi=300, bbox_inches='tight', pad_inches=0.3)
    print("✅ Saved performance_matrix.png")

    # 4. Momentum Velocity Bar Chart
    velocity_data = {
        'Velocity (Bets/7d)': ['Low (0-5)', 'Mid (5-15)', 'High (15-30)', 'Extreme (30+)'],
        'Win Rate': [0.5064, 0.5059, 0.5028, 0.5155]
    }
    df_velocity = pd.DataFrame(velocity_data)
    
    plt.figure(figsize=(10, 6))
    colors = [DIM_TEXT, KYANITE, CARNELIAN, '#ffffff']
    sns.barplot(data=df_velocity, x='Velocity (Bets/7d)', y='Win Rate', palette=colors)
    plt.axhline(0.50, color='#ffffff', linestyle='--', alpha=0.3)
    plt.title('MOMENTUM VELOCITY: IMPACT OF DENSITY', loc='left')
    plt.ylim(0.48, 0.53)
    plt.ylabel('WIN RATE (%)', fontfamily='monospace', fontsize=10, alpha=0.8)
    
    plt.savefig('research/momentum_velocity.png', dpi=300, bbox_inches='tight', pad_inches=0.2)
    print("✅ Saved momentum_velocity.png")

if __name__ == "__main__":
    generate_graphics()

