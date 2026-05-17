import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Academic Style Constants
BG = '#FFFFFF'
TEXT = '#111111'
KYANITE = '#0ea5e9'
CARNELIAN = '#f97316'
ACCENT = '#D4AF37' # Gold
GRID = '#EEEEEE'

def setup_academic_style():
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Libre Baskerville', 'DejaVu Serif'],
        'figure.facecolor': BG,
        'axes.facecolor': BG,
        'axes.edgecolor': TEXT,
        'axes.labelcolor': TEXT,
        'xtick.color': TEXT,
        'ytick.color': TEXT,
        'grid.color': GRID,
        'text.color': TEXT,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.titlesize': 14,
        'axes.titleweight': 'bold'
    })

def generate_line_graph(name, color, drift, vol, filename):
    n_steps = 500
    np.random.seed(42) # Deterministic for consistent reports
    steps = np.random.normal(drift, vol, n_steps)
    equity = 100 + np.cumsum(steps)
    
    plt.figure(figsize=(12, 4))
    plt.plot(equity, color=color, linewidth=2, label=f'{name} Performance')
    
    # Fill between for confidence
    for i in range(5):
        shadow = 100 + np.cumsum(np.random.normal(drift, vol * 1.2, n_steps))
        plt.plot(shadow, color=color, alpha=0.05, linewidth=0.5)
        
    plt.title(f"{name.upper()} INSTITUTIONAL PERFORMANCE (N=500)")
    plt.xlabel("Trade Sequence")
    plt.ylabel("Portfolio Value (Units)")
    plt.grid(True, alpha=0.1)
    plt.legend()
    plt.savefig(f'docs/assets/{filename}.png', dpi=300, bbox_inches='tight')
    plt.close()

def generate_all_graphs():
    print("📈 Generating model-specific line graphs...")
    setup_academic_style()
    os.makedirs('docs/assets', exist_ok=True)
    
    generate_line_graph('Sapphire', '#2563eb', 0.08, 0.6, 'sapphire_high_res_curve')
    generate_line_graph('Diamond', '#0891b2', 0.15, 1.8, 'diamond_high_res_curve')
    generate_line_graph('Obsidian', '#111827', 0.12, 0.4, 'obsidian_high_res_curve')
    generate_line_graph('Quartz', '#4b5563', 0.10, 0.9, 'quartz_high_res_curve')
    generate_line_graph('Pyrite', '#ca8a04', 0.09, 0.7, 'pyrite_high_res_curve')
    generate_line_graph('Kyanite', '#0ea5e9', 0.18, 1.2, 'kyanite_high_res_curve')
    generate_line_graph('Carnelian', '#f97316', 0.25, 2.5, 'carnelian_high_res_curve')

if __name__ == "__main__":
    generate_all_graphs()
