import os
import json
import pandas as pd
import joblib
from datetime import datetime
import sys

# [BILLION DOLLAR STABILITY]: Prevent Segfaults (Exit Code 139) on resource-constrained runners
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

# Path setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, 'src'))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from pipeline import SportsDataPipeline, FeatureEngineer
from models_legacy import ModelSimulator
from src.utils.logger import logger
from src.utils.validator import DataValidator
from src.utils.stats import StatsEngine

# --- PRE-FLIGHT CHECK ---
def pre_flight_check():
    """Verifies environment and critical files before starting the pipeline."""
    logger.info("🛫 Performing Pre-flight Integrity Check...")
    
    # 1. Check Env Vars
    required_env = ["SUPABASE_URL", "SUPABASE_KEY"]
    missing_env = [env for env in required_env if not os.environ.get(env)]
    if missing_env:
        logger.error(f"❌ Missing critical environment variables: {missing_env}")
        return False
        
    # 2. Check Model Files
    critical_models = ['v1_pyrite.pkl', 'v2_diamond.pkl', 'v4_quartz.pkl']
    missing_models = []
    for m in critical_models:
        path = os.path.join(BASE_DIR, 'models', m)
        if not os.path.exists(path):
            missing_models.append(m)
    
    if missing_models:
        logger.warning(f"⚠️ Missing model files: {missing_models}. Some models will be skipped.")
        
    logger.info("✅ Pre-flight Check Complete.")
    return True

def update_markdown_reports(models):
    """Updates README.md and LATEST_ACTION.md with latest results using StatsEngine."""
    logger.info("📝 Updating System Reports (README.md & LATEST_ACTION.md)...")
    
    # --- CALCULATE STATS USING StatsEngine ---
    stats = {}
    for name, df in models.items():
        stats[name] = StatsEngine.calculate_metrics(df)

    # [SURGICAL DNA]: Combined Series 6 Stats
    v6_list = [models.get('kyanite'), models.get('carnelian')]
    v6_list = [d for d in v6_list if d is not None and not d.empty]
    v6_df = pd.concat(v6_list) if v6_list else pd.DataFrame()
    stats_v6 = StatsEngine.calculate_metrics(v6_df)

    # --- 1. LATEST_ACTION.md ---
    et_now = StatsEngine.get_et_now()
    yesterday_data = StatsEngine.get_yesterday_data(v6_df, et_now=et_now) # Use V6 as primary for date
    display_date = yesterday_data['date'] if yesterday_data else (et_now - pd.Timedelta(days=1)).strftime('%b %d, %Y')
    
    log_content = f"# 📝 Daily Action Log ({display_date})\n\n"
    
    def make_table(df, title):
        if df is None or df.empty: return f"### {title}\n*No action found.*\n\n"
        
        # Use yesterday's data specifically if possible
        y = StatsEngine.get_yesterday_data(df, et_now=et_now)
        if not y or not y['ledger']:
             return f"### {title}\n*No action for this date.*\n\n"

        t = f"### {title}\n"
        t += "| LEAGUE | PICK | ODDS | UNIT | RES | PROFIT |\n"
        t += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        
        for row in y['ledger']:
            res = "✅" if row['result'] == "WIN" else "❌" if row['result'] == "LOSS" else "⏳"
            odds_text = f"+{row['odds']}" if row['odds'] > 0 else f"{row['odds']}"
            t += f"| {row['league']} | {row['selection']} | {odds_text} | {row['wager']:.1f} | {res} | {row['profit']:+.2f}u |\n"
        
        t += f"\n**Daily PnL: {y['net']:+.2f} Units**\n\n"
        return t + "\n"

    log_content += make_table(models.get("kyanite"), "Kyanite Action")
    log_content += make_table(models.get("carnelian"), "Carnelian Action")
    log_content += make_table(models.get("sapphire"), "V5 Sapphire Action")
    log_content += make_table(models.get("quartz"), "V4 Quartz Action")
    log_content += make_table(models.get("obsidian"), "V3 Obsidian Action")
    log_content += make_table(models.get("diamond"), "V2 Diamond Action")
    log_content += make_table(models.get("pyrite"), "V1 Pyrite Action")
    
    with open(os.path.join(BASE_DIR, "LATEST_ACTION.md"), "w", encoding="utf-8") as f:
        f.write(log_content)

    # --- 2. README.md ---
    def get_row(name, label, released, profile, color_emoji):
        m = stats.get(name, StatsEngine.calculate_metrics(None))
        return f"| **[{label}](https://ducky705.github.io/Quarry-Intelligence/web/{name if name != 'pyrite' else 'pyrite'}.html)** | `{released}` | `{profile}` | {color_emoji} **ACTIVE** | {m['volume']} | **{m['sample']}** | **{m['roi']:+.1%}** |"

    readme_text = f"""
<div align="center">
  <br />
  <h1>QUARRY INTELLIGENCE</h1>
  <p style="font-family: monospace; letter-spacing: 2px; color: #888;">INSTITUTIONAL ALGORITHMIC ANALYTICS</p>
  <br />

  <a href="https://ducky705.github.io/Quarry-Intelligence/web/selector.html">
    <img src="https://img.shields.io/badge/STATUS-OPERATIONAL-success?style=for-the-badge&logo=statuspage&logoColor=white" alt="Status" />
  </a>
  <a href="https://ducky705.github.io/Quarry-Intelligence/web/kyanite_carnelian.html">
    <img src="https://img.shields.io/badge/SERIES%206%20NET-{stats_v6['net']:+.1f}u-D4AF37?style=for-the-badge" alt="Series 6 Net" />
  </a>
  <a href="https://ducky705.github.io/Quarry-Intelligence/web/sapphire.html">
    <img src="https://img.shields.io/badge/SERIES%205%20NET-{stats.get('sapphire', {'net':0})['net']:+.1f}u-2563EB?style=for-the-badge" alt="Series 5 Net" />
  </a>
  <a href="https://ducky705.github.io/Quarry-Intelligence/web/quartz.html">
    <img src="https://img.shields.io/badge/SERIES%204%20NET-{stats.get('quartz', {'net':0})['net']:+.1f}u-f8fafc?style=for-the-badge" alt="Series 4 Net" />
  </a>

  <br />
  <br />
  <a href="https://ducky705.github.io/Quarry-Intelligence/web/selector.html"><strong>ACCESS CONTROL CENTER</strong></a>
  <br />
  <br />
</div>

---

## ⚡ EXECUTIVE INTELLIGENCE

A multi-generational algorithmic trading system leveraging **Gradient Boosting Decision Trees (XGBoost)** and **Deep Neural Networks** to identify inefficiencies in sports betting markets.

| MODEL ARCHITECTURE | RELEASED | STRATEGY PROFILE | STATUS | VOLUME | TOTAL BETS | ROI |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **[SERIES 6: KYANITE & CARNELIAN](https://ducky705.github.io/Quarry-Intelligence/web/kyanite_carnelian.html)** | `MAY 16, 2026` | `SURGICAL ALPHA` <br> Precision/Yield | 💎 **ACTIVE** | {stats_v6['volume']} | **{stats_v6['sample']}** | **{stats_v6['roi']:+.1%}** |
{get_row('sapphire', 'SERIES 5: SAPPHIRE', 'MAY 13, 2026', 'CONFORMAL <br> Momentum', '🔵')}
{get_row('quartz', 'SERIES 4: QUARTZ', 'APR 06, 2026', 'INSTITUTIONAL <br> Drift Proxy', '⚪')}
{get_row('obsidian', 'SERIES 3: OBSIDIAN', 'DEC 27, 2025', 'ADVANCED ENSEMBLE <br> Non-Linear', '🟣')}
{get_row('diamond', 'SERIES 2: DIAMOND', 'NOV 30, 2025', 'PRECISION CORE <br> Refined', '🟢')}
{get_row('pyrite', 'SERIES 1: PYRITE', 'NOV 20, 2025', 'LEGACY CORE <br> High-Freq', '🟡')}

> [!IMPORTANT]
> **ACCESS PROTOCOL**: The primary interface for all models is the [**Model Selector**](https://ducky705.github.io/Quarry-Intelligence/web/selector.html).

---

## 🛰 SYSTEMS OVERVIEW

### V6 KYANITE & CARNELIAN // THE SURGICAL DNA
*The next evolution.* A dual-engine framework balancing high-threshold precision (Kyanite) with maximum Bayesian value (Carnelian).
*   **Mechanism**: Leverages "Surgical DNA" sequencing to isolate institutional-grade win thresholds and high-edge underdog windows.
*   **Performance**: Optimized for both optical consistency and pure mathematical alpha.

### V5 SAPPHIRE // THE CONFORMAL ENGINE
*The definitive shift.* Employs **Split Conformal Prediction** and **Dynamic Momentum** to bound risk and capture institutional-grade win thresholds.
*   **Mechanism**: Asymmetric loss optimization with drift-aware feature engineering.
*   **Performance**: Targeting maximum precision and high-fidelity alpha.

### V4 QUARTZ // THE PRISM
*The flagship standard.* Utilizes **Correct Shift** logic to identify opening line inefficiencies.

---

## 📚 KNOWLEDGE BASE

### 🔬 DEEP INTELLIGENCE REPORTS
Comprehensive technical audits and strategy profiles for the current model lineup.

*   **[SERIES 6: KYANITE & CARNELIAN Audit](docs/reports/KYANITE_REPORT.md)** - Surgical Alpha, Precision & Liquidity Optimization
*   **[SERIES 5: SAPPHIRE Audit](docs/reports/SAPPHIRE_REPORT.md)** - Conformal Prediction & Momentum
*   **[SERIES 4: QUARTZ Audit](docs/reports/QUARTZ_REPORT.md)** - Institutional Drift Proxy
*   **[SERIES 3: OBSIDIAN Audit](docs/reports/OBSIDIAN_REPORT.md)** - Advanced Non-Linear Ensembles
*   **[SERIES 2: DIAMOND Audit](docs/reports/DIAMOND_REPORT.md)** - Precision Core & Refined Filtering
*   **[SERIES 1: PYRITE Audit](docs/reports/PYRITE_REPORT.md)** - Legacy High-Frequency Core

### 🏛️ LEGACY ARCHIVES
Historical research, methodology versions, and experimental results.

*   **[Deep Mining Report](docs/archive/DEEP_MINING_REPORT.md)** - Foundational research on market inefficiencies.
*   **[Momentum Physics](docs/archive/MOMENTUM_PHYSICS.md)** - Theoretical basis for V5 velocity engines.
*   **[Quantum Results](docs/archive/QUANTUM_RESULTS.md)** - Experimental V4 quantum-enhanced backtests.
*   **[Stress Test Results](docs/archive/STRESS_TEST_RESULTS.md)** - Robustness analysis under extreme market drift.
*   **[Methodology V2](docs/archive/methodology_v2.md)** | **[Methodology V1](docs/archive/methodology_v1.md)**

---

## 🛠 ARCHITECTURE

```mermaid
graph TD
    A[DATA LAKE] -->|Ingest| B(CORE ENGINE)
    B -->|Feature Engineering| C{{MODEL SELECTOR}}
    C -->|Legacy| D[V1 PYRITE]
    C -->|Stable| E[V2 DIAMOND]
    C -->|Advanced| F[V3 OBSIDIAN]
    C -->|Flagship| G[V4 QUARTZ]
    C -->|Premium| J[V5 SAPPHIRE]
    C -->|Surgical| K[V6 KYANITE & CARNELIAN]
    D & E & F & G & J & K -->|Simulate| H[DECISION SUPPORT]
    H -->|Render| I[DASHBOARD SUITE]
```

---

<div align="center">
    <p><em>© 2026 QUARRY INTELLIGENCE GROUP // PROPRIETARY RESEARCH</em></p>
</div>
"""
    
    with open(os.path.join(BASE_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_text)
        
    print("✅ System reports updated.")

def run_daily_update():
    logger.info("🚀 Starting Daily Update Pipeline")
    
    # [BILLION DOLLAR GUARD]: Ensure script only runs once per day
    last_run_file = os.path.join(BASE_DIR, 'docs', 'last_run.txt')
    force_update = os.environ.get('FORCE_UPDATE') == 'true' or '--force' in sys.argv
    et_now = StatsEngine.get_et_now()
    
    if os.path.exists(last_run_file) and not force_update:
        try:
            with open(last_run_file, 'r') as f:
                content = f.read()
                if "Last successful run:" in content:
                    date_str = content.split("Last successful run:")[1].strip()
                    today_et = et_now.strftime('%b %d')
                    year_et = et_now.strftime('%Y')
                    
                    if today_et in date_str and year_et in date_str:
                        logger.info(f"🛑 Pipeline already completed successfully today ({date_str}). Skipping run.")
                        return
        except Exception as e:
            logger.warning(f"⚠️ Could not verify last run date: {e}. Proceeding anyway.")

    if not pre_flight_check():
        logger.error("❌ Pre-flight check failed. Aborting.")
        sys.exit(1)
    
    # 1. Fetch & Hydrate Data
    try:
        pipeline = SportsDataPipeline()
        raw_df = pipeline.fetch_data_cached() # Incremental update
        
        if not raw_df.empty:
            logger.info(f"📊 Pipeline Data Range: {raw_df['pick_date'].min().date()} to {raw_df['pick_date'].max().date()}")
        else:
            logger.error("❌ Pipeline Data is EMPTY! Cannot proceed.")
            sys.exit(1)

        fe = FeatureEngineer(raw_df)
        df = fe.process()
        
        ms = ModelSimulator(df)
    except Exception as e:
        logger.error(f"❌ Initialization Error: {e}")
        sys.exit(1)
    
    # 2. Run Simulations
    logger.info("⏳ Running Multi-Generational Simulations...")
    models = {}
    
    simulation_tasks = [
        ("pyrite", ms.run_v1_pyrite),
        ("diamond", ms.run_v2_diamond),
        ("obsidian", ms.run_v3_obsidian),
        ("quartz", ms.run_v4_quartz),
        ("sapphire", ms.run_v5_sapphire),
        ("kyanite", ms.run_Kyanite_kyanite),
        ("carnelian", ms.run_Carnelian_carnelian)
    ]
    
    for name, func in simulation_tasks:
        try:
            logger.info(f"  - Executing {name.upper()}...")
            res = func()
            models[name] = res
            logger.info(f"    ✅ {name.upper()}: {len(res) if res is not None else 0} picks identified.")
        except Exception as e:
            logger.error(f"    ❌ {name.upper()} Simulation Failed: {e}")
            models[name] = pd.DataFrame()
    
    # 3. Generate Stats for JSON/JS
    et_now = StatsEngine.get_et_now()
    stats_output = {
        "meta": {
            "last_update": et_now.strftime('%Y-%m-%d %H:%M ET'),
            "status": "NOMINAL",
            "cache_bust": et_now.timestamp()
        },
        "models": {}
    }
    
    for name, res in models.items():
        m = StatsEngine.calculate_metrics(res)
        y = StatsEngine.get_yesterday_data(res, et_now=et_now)
        
        stats_output["models"][name] = {
            "roi": round(m['roi'] * 100, 1),
            "net": round(m['net'], 1),
            "wins": m['wins'],
            "losses": m['losses'],
            "pushes": m['pushes'],
            "record": m['record'],
            "win_rate": round(m['win_rate'] * 100, 1),
            "sample": m['sample'],
            "bets_day": 0.0, # Placeholder, filled below
            "status": "ACTIVE",
            "yesterday": y if y else {"date": "N/A", "record": "0-0-0", "win_rate": 0, "net": 0, "roi": 0, "ledger": []}
        }
        # Parse volume for bets_day float
        try:
             import re
             avg_match = re.search(r'~?(\d+)', m['volume'])
             stats_output["models"][name]["bets_day"] = float(avg_match.group(1)) if avg_match else 0.0
        except:
             stats_output["models"][name]["bets_day"] = 0.0

    # 4. Save Stats
    docs_dir = os.path.join(BASE_DIR, 'docs')
    web_dir = os.path.join(docs_dir, 'web')
    os.makedirs(web_dir, exist_ok=True)
    
    for target_dir in [docs_dir, web_dir]:
        with open(os.path.join(target_dir, 'stats.json'), 'w') as f:
            json.dump(stats_output, f, indent=4)
            
        with open(os.path.join(target_dir, 'stats.js'), 'w') as f:
            f.write(f"window.QUARRY_STATS = {json.dumps(stats_output, indent=4)};")
        
    # [BILLION DOLLAR OPTIMIZATION]: Cache results
    cache_path = os.path.join(docs_dir, 'sim_results_cache.pkl')
    try:
        joblib.dump(models, cache_path)
        logger.info(f"📦 Simulation results cached to {cache_path}")
    except Exception as e:
        logger.error(f"❌ Failed to cache results: {e}")
        
    # 4c. Export Machine-Readable Summary for GHA
    summary = {
        "last_update": stats_output['meta']['last_update'],
        "data_range": f"{raw_df['pick_date'].min().date()} to {raw_df['pick_date'].max().date()}" if not raw_df.empty else "N/A",
        "total_rows": len(raw_df),
        "picks_identified": {m: len(models[m]) for m in models}
    }
    with open('docs/pipeline_summary.json', 'w') as f:
        json.dump(summary, f, indent=4)
        
    # [HEARTBEAT]: Update heartbeat file ONLY on successful data processing
    with open(last_run_file, 'w') as f:
        f.write(f"Last successful run: {et_now.strftime('%a %b %d %H:%M:%S ET %Y')}")

    # 5. Update Markdown Reports
    try:
        update_markdown_reports(models)
    except Exception as e:
        logger.error(f"❌ Failed to update markdown reports: {e}")

    # 6. Generate Assets (Plots & HTML Injection)
    logger.info("🎨 Generating Assets...")
    try:
        import scripts.generate_assets as generate_assets
        generate_assets.generate_live_assets(models=models)
    except Exception as e:
        logger.error(f"❌ Asset Generation Failed: {e}")
    
    # 7. Generate Comparison Graphics
    try:
        if os.path.join(BASE_DIR, 'research') not in sys.path:
            sys.path.append(os.path.join(BASE_DIR, 'research'))
        import generate_comparison
        generate_comparison.generate_comparison_chart()
    except Exception as e:
        logger.error(f"❌ Comparison Chart Generation Failed: {e}")
    
    logger.info("✅ Daily Update Complete.")

if __name__ == "__main__":
    run_daily_update()
