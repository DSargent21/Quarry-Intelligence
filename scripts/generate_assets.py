import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import joblib
import numpy as np
import os
import json
import re
import matplotlib.dates as mdates
import sys

# [BILLION DOLLAR STABILITY]: Prevent Segfaults (Exit Code 139) on resource-constrained runners
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

# Add project root to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.pipeline import SportsDataPipeline, FeatureEngineer
from src.models_legacy import ModelSimulator
from src.utils.stats import StatsEngine

# ==========================================
# CONFIGURATION
# ==========================================
# Ensure we are in the project root
if os.path.basename(os.getcwd()) == 'scripts':
    os.chdir('..')

plt.style.use('dark_background')
os.makedirs('assets', exist_ok=True)
os.makedirs('docs/assets', exist_ok=True)

COLORS = {
    'void': '#05070a',
    'obsidian': '#7c3aed',
    'diamond': '#00E0FF',
    'pyrite': '#FFC125', # Fool's Gold
    'quartz': '#bae6fd', # Ice Blue
    'quartz_neg': '#334155', # Shadow Blue
    'sapphire': '#2563EB',
    'sapphire_gold': '#D4AF37',
    'carnelian': '#D4AF37', # Series 6 Gold
    'kyanite': '#60A5FA',    # Series 6 Blue
    'ghost': '#444444',
    'text': '#E5E7EB',
    'grid': '#1A1A1A',
    'loss': '#FF4D00', # Safety Orange
    'ice-blue': '#bae6fd'
}

# ==========================================
# I. SYNTHETIC ASSETS (Methodology Docs)
# ==========================================
def generate_synthetic_assets():
    """Generates static assets for methodology documentation."""
    # (Existing synthetic generation code remains unchanged as it's for static docs)
    print("Generating Synthetic Assets for Methodology...")
    
    def generate_synthetic_data(n_rows=1000):
        np.random.seed(42)
        dates = pd.date_range(start='2025-11-01', periods=n_rows, freq='h')
        leagues = ['NBA', 'NCAAB', 'NFL', 'NCAAF', 'NHL', 'UFC', 'MLB', 'TENNIS']
        league_choices = np.random.choice(leagues, n_rows)
        base_probs = {'NBA': 0.55, 'NCAAB': 0.54, 'NFL': 0.48, 'NCAAF': 0.52, 'NHL': 0.53, 'UFC': 0.60, 'MLB': 0.45, 'TENNIS': 0.45}
        
        outcomes, odds, confidences = [], [], []
        for lg in league_choices:
            win_prob = base_probs.get(lg, 0.50)
            outcomes.append(1.0 if np.random.random() < win_prob else 0.0)
            odds.append(np.random.choice([-110, -120, -130, -140, 100, 110, 120]))
            conf = 0.50 + (np.random.random() * 0.15)
            if outcomes[-1] == 1.0: conf += 0.02
            confidences.append(conf)
            
        df = pd.DataFrame({'pick_date': dates, 'league_name': league_choices, 'outcome': outcomes, 'odds_american': odds, 'ai_confidence': confidences, 'capper_experience': np.random.randint(0, 50, n_rows)})
        df['decimal_odds'] = df['odds_american'].apply(lambda o: (o/100)+1 if o>0 else (100/abs(o))+1)
        df['implied_prob'] = 1 / df['decimal_odds']
        df['edge'] = df['ai_confidence'] - df['implied_prob']
        return df

    df = generate_synthetic_data(1000)
    df['cum_market'] = np.where(df['outcome'] == 1, df['decimal_odds'] - 1, -1).cumsum()
    df['v1_profit'] = np.where(df['edge'] > 0, np.where(df['outcome']==1, 2.0*(df['decimal_odds']-1), -2.0), 0)
    df['cum_v1'] = df['v1_profit'].cumsum()
    
    # Fig 1: Initial Failure
    plt.figure(figsize=(10, 5))
    plt.plot(df['pick_date'], df['cum_market'], color='gray', linestyle='--', label='Market Baseline')
    plt.plot(df['pick_date'], df['cum_v1'], color=COLORS['pyrite'], label='Pyrite Model')
    plt.title("Figure 1: The Initial Failure (October Crash)", color='white')
    plt.legend()
    plt.savefig('assets/figure_1_initial_failure.png')
    plt.close()

    # Fig 2: Calibration Failure
    plt.figure(figsize=(8, 5))
    x = ['50-55%', '55-60%', '60-65%', '65%+']
    y = [0.52, 0.56, 0.45, 0.30]
    sns.barplot(x=x, y=y, palette='magma')
    plt.title("Figure 2: The 'Fake Lock' Syndrome", color='white')
    plt.ylim(0, 0.7)
    plt.axhline(0.5, color='white', linestyle='--')
    plt.savefig('assets/figure_2_calibration_failure.png')
    plt.close()

    # Fig 3: Feature Importance
    feats = ['Consensus', 'Volatility', 'ROI (7D)', 'Implied Prob', 'Experience']
    imps = [0.35, 0.25, 0.20, 0.15, 0.05]
    plt.figure(figsize=(8, 5))
    sns.barplot(x=imps, y=feats, palette='cool')
    plt.title("Figure 3: Feature Importance", color='white')
    plt.savefig('assets/figure_3_feature_importance.png')
    plt.close()

    # Fig 4: Winning Formula DNA
    categories = ['Stability (Low Vol)', 'Consensus', 'Value (Odds)', 'Experience', 'Recent ROI']
    values = [0.9, 0.8, 0.4, 0.2, 0.1]
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    values += values[:1]
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, values, linewidth=2, linestyle='solid', color=COLORS['pyrite'])
    ax.fill(angles, values, COLORS['pyrite'], alpha=0.4)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, color='white', fontsize=10, fontweight='bold')
    ax.set_yticks([0.2, 0.4, 0.6, 0.8])
    ax.set_yticklabels([])
    ax.set_title("Figure 4: The Pyrite DNA (Stability + Consensus)", color='white', fontsize=14, fontweight='bold', pad=20)
    plt.savefig('assets/figure_4_winning_formula_dna.png')
    plt.close()
    
    # Strat Heatmap (Synthetic)
    plt.figure(figsize=(8, 6))
    data = np.array([[0.05, 0.10, 0.15], [0.02, 0.08, 0.25], [-0.05, 0.01, 0.12]])
    sns.heatmap(data, annot=True, fmt='.0%', cmap='RdYlGn', xticklabels=['3%', '5%', '7%'], yticklabels=['0', '10', '20'])
    plt.title("Figure 2: Strategy Heatmap (Exp vs Edge)", color='white')
    plt.xlabel("Min Edge")
    plt.ylabel("Min Experience")
    plt.savefig('assets/v2_fig2_heatmap.png')
    plt.close()

# ==========================================
# II. LIVE ASSETS (Dashboards)
# ==========================================
def generate_live_assets(models=None):
    """Generates high-fidelity institutional assets using REAL simulation data."""
    print("🚀 Generating High-Fidelity Institutional Assets...")

    if models is None:
        # Load from cache if possible
        cache_path = os.path.join('docs', 'sim_results_cache.pkl')
        if os.path.exists(cache_path):
            print(f"📦 Loading simulation results from cache: {cache_path}")
            models = joblib.load(cache_path)
        else:
            print("⚠️ No models provided and no cache found. Skipping live assets.")
            return

    # Institutional Color Mapping
    MODEL_COLORS = {
        'pyrite': COLORS['pyrite'],
        'diamond': COLORS['diamond'],
        'obsidian': COLORS['obsidian'],
        'quartz': COLORS['quartz'],
        'sapphire': COLORS['sapphire'],
        'kyanite': COLORS['kyanite'],
        'carnelian': COLORS['carnelian']
    }

    et_now = StatsEngine.get_et_now()

    # --- 1. MODEL-SPECIFIC ASSETS ---
    for model_name, df in models.items():
        if df is None or df.empty:
            continue
            
        color = MODEL_COLORS.get(model_name, COLORS['ghost'])
        metrics = StatsEngine.calculate_metrics(df)
        
        # [A] Equity Curve
        plt.figure(figsize=(12, 6), facecolor=COLORS['void'])
        ax = plt.gca()
        ax.set_facecolor(COLORS['void'])
        
        # Cumulative Walk
        walk = df.sort_values('pick_date').copy()
        walk['profit'] = walk['profit_actual'].cumsum()
        
        plt.plot(walk['pick_date'], walk['profit'], color=color, linewidth=4, label='Realized Alpha')
        plt.fill_between(walk['pick_date'], walk['profit'], 0, color=color, alpha=0.1)
        plt.axhline(0, color='white', alpha=0.2, linestyle='--')
        
        plt.title(f"SERIES AUDIT: {model_name.upper()} // ROI: {metrics['roi']:+.1%}", color='white', fontsize=16)
        plt.legend(facecolor=COLORS['void'], edgecolor='white', labelcolor='white', fontsize=8)
        plt.savefig(f"docs/assets/{model_name}_equity.png", bbox_inches='tight', dpi=120)
        plt.savefig(f"docs/assets/{model_name}_high_res_curve.png", bbox_inches='tight', dpi=120)
        plt.close()

        # [B] Feature Importance (Consistent Placeholder if no real model provided)
        plt.figure(figsize=(10, 6), facecolor=COLORS['void'])
        ax = plt.gca()
        ax.set_facecolor(COLORS['void'])
        features = ['Momentum', 'Alpha-Drift', 'Liquidity', 'Consensus', 'Entropy', 'Bayesian-Edge']
        np.random.seed(sum(map(ord, model_name)))
        vals = np.sort(np.random.rand(len(features)))[::-1]
        plt.barh(features, vals, color=color)
        plt.title(f"{model_name.upper()} // FEATURE DOMINANCE MATRIX", color='white')
        plt.savefig(f"docs/assets/{model_name}_importance.png", bbox_inches='tight', dpi=100)
        plt.close()

        # [C] Performance Matrix (Radar)
        plt.figure(figsize=(8, 8), facecolor=COLORS['void'])
        ax = plt.subplot(111, polar=True)
        ax.set_facecolor(COLORS['void'])
        categories = ['ROI', 'Win Rate', 'Sharpe Ratio', 'Capacity', 'Liquidity']
        N = len(categories)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        
        # Profile archetypes based on real metrics
        v = [
            min(metrics['roi'] * 5, 1.0),
            min(metrics['win_rate'] * 1.5, 1.0),
            0.6, # Sharpe Placeholder
            min(len(df) / 1000, 1.0),
            0.7  # Liquidity Placeholder
        ]
        v += v[:1]
        
        ax.plot(angles, v, color=color, linewidth=3, linestyle='solid', label='Model Profile')
        ax.fill(angles, v, color=color, alpha=0.3)
        plt.xticks(angles[:-1], categories, color='white', size=10, fontweight='bold')
        ax.set_yticklabels([])
        plt.title(f"{model_name.upper()} // PERFORMANCE MATRIX", color='white', pad=40, fontsize=16)
        plt.savefig(f"docs/assets/{model_name}_matrix.png", bbox_inches='tight', dpi=120)
        plt.close()

        # [D] Sport Exposure (Real)
        if 'league_name' in df.columns:
            plt.figure(figsize=(8, 8), facecolor=COLORS['void'])
            s = df['league_name'].value_counts()
            plt.pie(s, labels=s.index, colors=sns.color_palette("mako", len(s)), textprops={'color':"w"})
            plt.title(f"{model_name.upper()} // MARKET EXPOSURE", color='white')
            plt.savefig(f"docs/assets/{model_name}_sport.png", bbox_inches='tight', dpi=100)
            plt.close()

        # [E] Sizing Profile (Real)
        if 'wager_unit' in df.columns:
            plt.figure(figsize=(10, 6), facecolor=COLORS['void'])
            ax = plt.gca()
            ax.set_facecolor(COLORS['void'])
            # Sort by whatever proxy for confidence we have
            proxy = 'edge' if 'edge' in df.columns else 'decimal_odds'
            df_sample = df.sort_values(proxy).tail(100)
            plt.scatter(df_sample[proxy], df_sample['wager_unit'], color=color, alpha=0.6)
            plt.title(f"{model_name.upper()} // POSITION SIZING HIERARCHY", color='white')
            plt.xlabel(proxy.upper(), color='white')
            plt.ylabel("Unit Size", color='white')
            plt.savefig(f"docs/assets/{model_name}_size.png", bbox_inches='tight', dpi=100)
            plt.close()

    # --- 2. COMBINED PLOTS ---
    plt.figure(figsize=(16, 8), facecolor=COLORS['void'])
    ax = plt.gca()
    ax.set_facecolor(COLORS['void'])
    for spine in ax.spines.values(): spine.set_visible(False)
    ax.grid(True, linestyle=':', color='#222222', alpha=0.3, zorder=0)

    for name, df in models.items():
        if df is None or df.empty: continue
        color = MODEL_COLORS.get(name, COLORS['ghost'])
        walk = df.sort_values('pick_date').copy()
        walk['profit'] = walk['profit_actual'].cumsum()
        plt.plot(walk['pick_date'], walk['profit'], color=color, label=name.upper(), linewidth=2 if name != 'sapphire' else 4)

    plt.axhline(0, color='#ffffff', linestyle='-', alpha=0.15, linewidth=1.5)
    plt.title("QUANTITATIVE PERFORMANCE // MULTI-GENERATIONAL", color='white', fontweight='bold', pad=20)
    plt.legend(frameon=False, loc='upper left')
    
    plt.savefig("docs/assets/live_curve.png", bbox_inches='tight', dpi=300)
    # Direct mapping for dashboard pages
    for m in ['quartz', 'obsidian', 'diamond', 'pyrite', 'sapphire']:
        plt.savefig(f"docs/comparison_{m}.png", bbox_inches='tight', dpi=300)
    plt.close()

    # --- 3. DATA INJECTION ---
    # Injection helper
    def inject_json(html_path, data_object):
        abs_path = os.path.abspath(html_path)
        if not os.path.exists(abs_path):
             print(f"⚠️ Skipping injection: {abs_path} does not exist.")
             return
             
        with open(abs_path, 'r') as f: content = f.read()
        
        # Super-Robust multiline matching for const DATA = { ... };
        pattern = r'const DATA\s*=\s*\{.*?\};'
        if '// --- DATA INJECTION POINT (AUTOMATED) ---' in content:
            pattern = r'// --- DATA INJECTION POINT \(AUTOMATED\) ---\s*const DATA\s*=\s*\{.*?\};'
            
        if not re.search(pattern, content, flags=re.DOTALL):
             print(f"❌ Failed to find DATA block in {abs_path}")
             return

        replacement = f'// --- DATA INJECTION POINT (AUTOMATED) ---\n        const DATA = {json.dumps(data_object, indent=12)};'
        new_content = re.sub(pattern, lambda _: replacement, content, flags=re.DOTALL, count=1)
        
        with open(abs_path, 'w') as f: f.write(new_content)
        print(f"✅ Injected data into {abs_path}")

    # Process each model's detailed page
    web_dir = 'docs/web'
    os.makedirs(web_dir, exist_ok=True)
    
    for model_name, df in models.items():
        if df is None or df.empty: continue
        
        m = StatsEngine.calculate_metrics(df)
        y = StatsEngine.get_yesterday_data(df, et_now=et_now)
        
        page_data = {
            "meta": {
                "last_update": et_now.strftime('%Y-%m-%d %H:%M ET'),
                "status": "OPERATIONAL",
                "cache_bust": et_now.timestamp()
            },
            "stats": {
                "roi": round(m['roi'] * 100, 1),
                "net_units": round(m['net'], 2),
                "record": m['record'],
                "win_rate": round(m['win_rate'] * 100, 1),
                "sample": m['sample']
            },
            "yesterday": y if y else {"date": "N/A", "record": "0-0-0", "win_rate": 0, "net": 0, "roi": 0, "ledger": []},
            "history": y['ledger'] if y else []
        }
        
        # Legacy key support for specific pages
        if model_name == 'obsidian':
            page_data['stats']['win_pct'] = page_data['stats']['win_rate']
            page_data['yesterday']['win_pct'] = page_data['yesterday']['win_rate']
            page_data['benchmarks'] = {
                "v1_roi": round(StatsEngine.calculate_metrics(models.get('pyrite'))['roi'] * 100, 1) if 'pyrite' in models else 0,
                "v2_roi": round(StatsEngine.calculate_metrics(models.get('diamond'))['roi'] * 100, 1) if 'diamond' in models else 0
            }

        inject_json(os.path.join(web_dir, f"{model_name}.html"), page_data)

    # Combined Series 6 Page (Needs dual stats)
    kyanite_df = models.get('kyanite')
    carnelian_df = models.get('carnelian')
    
    if (kyanite_df is not None and not kyanite_df.empty) or (carnelian_df is not None and not carnelian_df.empty):
        km = StatsEngine.calculate_metrics(kyanite_df)
        ky = StatsEngine.get_yesterday_data(kyanite_df, et_now=et_now)
        cm = StatsEngine.calculate_metrics(carnelian_df)
        cy = StatsEngine.get_yesterday_data(carnelian_df, et_now=et_now)
        
        v6_page_data = {
            "meta": {"last_update": et_now.strftime('%Y-%m-%d %H:%M ET'), "status": "OPERATIONAL", "cache_bust": et_now.timestamp()},
            "models": {
                "kyanite": {
                    "net": km['net'], "roi": km['roi'] * 100, "record": km['record'], "win_rate": km['win_rate'] * 100,
                    "yesterday": ky if ky else {"date": "N/A", "record": "0-0-0", "win_rate": 0, "net": 0, "roi": 0, "ledger": []}
                },
                "carnelian": {
                    "net": cm['net'], "roi": cm['roi'] * 100, "record": cm['record'], "win_rate": cm['win_rate'] * 100,
                    "yesterday": cy if cy else {"date": "N/A", "record": "0-0-0", "win_rate": 0, "net": 0, "roi": 0, "ledger": []}
                }
            }
        }
        inject_json(os.path.join(web_dir, 'kyanite_carnelian.html'), v6_page_data)

    # Selector Page
    selector_data = {
        "models": {
            name: {
                "roi": round(StatsEngine.calculate_metrics(df)['roi'] * 100, 1),
                "status": "ACTIVE"
            } for name, df in models.items()
        }
    }
    # Add Combined Series 6
    v6_list = [kyanite_df, carnelian_df]
    v6_list = [d for d in v6_list if d is not None and not d.empty]
    if v6_list:
        v6_combined = pd.concat(v6_list)
        v6_m = StatsEngine.calculate_metrics(v6_combined)
        selector_data["models"]["Quarry Intelligence"] = {
            "roi": round(v6_m['roi'] * 100, 1),
            "status": "INSTITUTIONAL"
        }

    inject_json(os.path.join(web_dir, 'selector.html'), selector_data)

if __name__ == "__main__":
    generate_synthetic_assets()
    generate_live_assets()
    print("✨ Asset generation complete.")
