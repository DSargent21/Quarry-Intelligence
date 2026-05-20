import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from pipeline import SportsDataPipeline, FeatureEngineer
from models_legacy import ModelSimulator

def generate_comparison_chart(models=None):
    print("🚀 Generating Comparative Alpha Graphs...")
    
    if models is None:
        # Initialize Pipeline & Hydrate Features
        pipeline = SportsDataPipeline()
        raw_df = pipeline.fetch_data_cached() # Uses cache
        
        fe = FeatureEngineer(raw_df)
        df = fe.process() # Fully hydrated with v4 (shifted) and v3 (leaked) features
        
        simulator = ModelSimulator(df)

        # Run Simulations
        print("🌌 Simulating Quartz (Backtest Alpha)...")
        quartz_res = simulator.run_backtest_all() # Use full history for graph
        
        print("🌋 Simulating Obsidian...")
        obsidian_res = simulator.run_v3_obsidian()
        
        # For Pyrite and Diamond, if simulator doesn't have specific methods, 
        # we'll simulate them via edge filters (as they are usually based on Min_Edge)
        print("💎 Simulating Diamond (Surgical)...")
        diamond_res = simulator.run_v2_diamond() # Assuming it exists or fallback
        
        print("☄️ Simulating Pyrite (Aggressive)...")
        pyrite_res = simulator.run_v1_pyrite() # Assuming it exists or fallback
    else:
        print("📦 Using provided model results from primary pipeline...")
        quartz_res = models.get("quartz", pd.DataFrame())
        obsidian_res = models.get("obsidian", pd.DataFrame())
        diamond_res = models.get("diamond", pd.DataFrame())
        pyrite_res = models.get("pyrite", pd.DataFrame())

    # Extract Cumulative Series
    def get_series(res_df, label):
        if res_df is None or res_df.empty or 'pick_date' not in res_df.columns: 
            return pd.Series(dtype=float, name=label)
        
        # Chronological Sort
        res_df = res_df.sort_values('pick_date').copy()
        
        # Cumulative Profit
        res_df['cum_profit'] = res_df['profit_actual'].cumsum()
        
        # Aggregate by timestamp to ensure unique index for concat
        # We take the 'last' cumulative value for any picks at the exact same time
        series = res_df.groupby('pick_date')['cum_profit'].last()
        
        # Zero-Origin alignment: Prepend a 0.0 point just before the first action
        if not series.empty:
            first_pick_time = series.index.min()
            start_time = first_pick_time - pd.Timedelta(seconds=1)
            series[start_time] = 0.0
            series = series.sort_index()
            
        series.name = label
        return series

    q_series = get_series(quartz_res, 'v4 Quartz')
    o_series = get_series(obsidian_res, 'v3 Obsidian')
    d_series = get_series(diamond_res, 'v2 Diamond')
    p_series = get_series(pyrite_res, 'v1 Pyrite')

    # Merge and FIX: Explicitly name and SORT
    bench = pd.concat([q_series, o_series, d_series, p_series], axis=1)
    bench.columns = ['v4 Quartz', 'v3 Obsidian', 'v2 Diamond', 'v1 Pyrite']
    # FIX: Remove fillfill(0). NaNs will prevent the line from starting too early.
    bench = bench.sort_index().ffill()

    print("\n📈 CURRENT PERFORMANCE BENCHMARKS:")
    for col in bench.columns:
        val = bench[col].dropna().iloc[-1] if not bench[col].dropna().empty else 0
        print(f"  {col}: {val:.2f}u")
    
    colors = {
        'v1 Pyrite': '#ffdd00',      # Gold/Pyrite
        'v2 Diamond': '#00f0ff',     # Ice/Diamond
        'v3 Obsidian': '#7c3aed',    # Purple/Obsidian
        'v4 Quartz': '#f8fafc'       # White/Quartz
    }

    plt.style.use('dark_background')

    # --- GENERATE 4 FOCUSED VERSIONS ---
    focus_models = [
        ('pyrite', 'v1 Pyrite'),
        ('diamond', 'v2 Diamond'),
        ('obsidian', 'v3 Obsidian'),
        ('quartz', 'v4 Quartz')
    ]

    for page_id, focus_label in focus_models:
        # --- PANAVISION RATIO: 16x10 for symmetrical dashboard parity ---
        fig, ax = plt.subplots(figsize=(16, 10), facecolor='none')
        ax.set_facecolor('none')
        
        # Enforce absolute full-bleed
        ax.set_position([0, 0, 1, 1])
        
        # --- INSTITUTIONAL SCAFFOLDING ---
        # Subtle dotted grid for structural grounding
        ax.grid(True, linestyle=':', color='#222222', alpha=0.3, zorder=0)
        ax.axhline(0, color='#333333', linewidth=0.8, alpha=0.5, zorder=1)

        # --- ELITE FOCUS STYLING ---
        for col in bench.columns:
            series_name = str(col)
            is_focus = (series_name == focus_label)
            
            curr_series = bench[col].dropna()
            if curr_series.empty: continue

            color = colors.get(series_name, '#ffffff')
            if not is_focus:
                alpha = 0.35 # Enhanced visibility for background models
                lw = 1.0
                zorder = 5
            else:
                alpha = 1.0
                lw = 4.0 # Slightly thicker for 16x7
                zorder = 100
            
            smooth_values = curr_series.rolling(window=3, min_periods=1).mean()
            
            # 1. Background / Comparison Line
            ax.plot(curr_series.index, smooth_values, color=color, linewidth=lw, alpha=alpha, zorder=zorder)
            
            if is_focus:
                # 2. Institutional Aura (Fill-Under)
                # Layered alpha fills for a 'fintech' volume feel
                ax.fill_between(curr_series.index, smooth_values, -200, color=color, alpha=0.03, zorder=zorder-5)
                ax.fill_between(curr_series.index, smooth_values, -200, color=color, alpha=0.015, zorder=zorder-6)
                
                # 3. Outer Glow Layers
                for i in range(1, 4): 
                    ax.plot(curr_series.index, smooth_values, color=color, linewidth=lw + i*3, alpha=0.01, zorder=zorder-1)
                
                # 4. Neon Termination Orb (The 'Live' Point)
                last_time = curr_series.index[-1]
                last_val = smooth_values.iloc[-1]
                
                # Glowing Scatter Point
                ax.scatter(last_time, last_val, color='#ffffff', s=100, zorder=zorder+10, edgecolors=color, linewidths=2.5)
                ax.scatter(last_time, last_val, color=color, s=350, zorder=zorder+5, alpha=0.3) # Core glow
                ax.scatter(last_time, last_val, color=color, s=800, zorder=zorder+4, alpha=0.1) # Outer glow

        # --- DYNAMIC HEADROOM (Absolute Collision Avoidance) ---
        focus_series = bench[focus_label].dropna()
        if focus_series.empty:
            ax.set_ylim(-5, 15)
        else:
            f_min, f_max = focus_series.min(), focus_series.max()
            delta = f_max - f_min
            
            # Institutional Spacing: 
            # 25% top margin (harmonized for 16x7). 10% bottom for floor stability.
            if delta < 10:
                ax.set_ylim(f_min - 5, f_max + 25)
            else:
                ax.set_ylim(f_min - delta*0.1, f_max + delta*0.25)

        # --- FULL BLEED FORMATTING ---
        ax.set_axis_off() 
        for spine in ax.spines.values(): spine.set_visible(False) 
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        
        out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'docs', f'comparison_{page_id}.png'))
        
        # Save with Ultra-DPI for crispness in 1200px+ containers
        plt.savefig(out_path, dpi=400, transparent=True)
        plt.close(fig)
        print(f"✅ Full-Bleed PNG saved: {out_path}")

if __name__ == "__main__":
    generate_comparison_chart()
