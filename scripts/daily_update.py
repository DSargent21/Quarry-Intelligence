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
    critical_models = ['v1_pyrite.pkl', 'v2_diamond.pkl', 'v4_quartz.pkl', 'v6_micro_sniper.pkl']
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

    # [PAGES DOMAIN]: Single source of truth for the GitHub Pages base URL.
    # Keep this in sync when the GitHub username changes.
    PAGES_BASE = "https://dsargent21.github.io/Quarry-Intelligence"

    # --- CALCULATE STATS USING StatsEngine ---
    stats = {}
    for name, df in models.items():
        stats[name] = StatsEngine.calculate_metrics(df)

    # [SURGICAL DNA]: Combined Series 6 Stats
    v6_list = [models.get('kyanite'), models.get('carnelian')]
    v6_list = [d for d in v6_list if d is not None and not d.empty]
    v6_df = pd.concat(v6_list) if v6_list else pd.DataFrame()
    stats_v6 = StatsEngine.calculate_metrics(v6_df)

    # [FORWARD TEST]: Series 7 Ruby stats from the frozen walk-forward ledger.
    # docs/ruby_forward.json is written by ruby/forward.py later in the same
    # pipeline run (and is tracked, so last run's file is present at checkout).
    ruby_stats = {"sample": 0, "net": 0.0, "roi": None,
                  "verification": {"n": 307, "roi": 0.110, "tstat": 2.04,
                                    "profit": 33.8, "months_pos": "3/3"}}
    ruby_forward_path = os.path.join(BASE_DIR, "docs", "ruby_forward.json")
    if os.path.exists(ruby_forward_path):
        try:
            with open(ruby_forward_path, "r", encoding="utf-8") as f:
                ruby_payload = json.load(f)
            rs = ruby_payload.get("stats", {})
            ruby_stats["sample"] = rs.get("n", 0)
            ruby_stats["net"] = rs.get("net", 0.0)
            ruby_stats["roi"] = rs.get("roi")
            ruby_stats["verification"] = (ruby_payload.get("meta", {})
                                           .get("verification", {})
                                           or ruby_stats["verification"])
        except Exception:
            logger.warning("⚠️ Could not parse docs/ruby_forward.json; Series 7 shown with defaults.")
    ruby_roi_text = f"{ruby_stats['roi']:+.1%}" if ruby_stats.get("roi") is not None else "—"

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
            t += f"| {row['league']} | {row['selection']} | {odds_text} | {row['wager']:.2f} | {res} | {row['profit']:+.2f}u |\n"
        
        t += f"\n**Daily PnL: {y['net']:+.2f} Units**\n\n"
        return t + "\n"

    log_content += make_table(models.get("kyanite"), "Kyanite Action")
    log_content += make_table(models.get("carnelian"), "Carnelian Action")
    log_content += make_table(models.get("sapphire"), "V5 Sapphire Action")
    log_content += make_table(models.get("quartz"), "V4 Quartz Action")
    log_content += make_table(models.get("obsidian"), "V3 Obsidian Action")
    log_content += make_table(models.get("diamond"), "V2 Diamond Action")
    log_content += make_table(models.get("pyrite"), "V1 Pyrite Action")
    
    log_path = os.path.abspath(os.path.join(BASE_DIR, "docs", "reports", "LATEST_ACTION.md"))
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(log_content)

    # --- 2. README.md ---
    def get_row(name, label, released, profile, color_emoji):
        m = stats.get(name, StatsEngine.calculate_metrics(None))
        return f"| **[{label}]({PAGES_BASE}/web/{name if name != 'pyrite' else 'pyrite'}.html)** | `{released}` | `{profile}` | {color_emoji} **ACTIVE** | {m['volume']} | **{m['sample']}** | **{m['roi']:+.1%}** |"

    readme_text = f"""
<div align="center">
  <br />
  <h1>QUARRY INTELLIGENCE</h1>
  <p style="font-family: monospace; letter-spacing: 2px; color: #888;">INSTITUTIONAL ALGORITHMIC ANALYTICS</p>
  <br />

  <a href="{PAGES_BASE}/web/selector.html">
    <img src="https://img.shields.io/badge/STATUS-OPERATIONAL-success?style=for-the-badge&logo=statuspage&logoColor=white" alt="Status" />
  </a>
  <a href="{PAGES_BASE}/web/kyanite_carnelian.html">
    <img src="https://img.shields.io/badge/SERIES%206%20NET-{stats_v6['net']:+.1f}u-D4AF37?style=for-the-badge" alt="Series 6 Net" />
  </a>
  <a href="{PAGES_BASE}/web/ruby.html">
    <img src="https://img.shields.io/badge/SERIES%207%20FWD-{ruby_stats['net']:+.1f}u-E11D48?style=for-the-badge" alt="Series 7 Forward Test" />
  </a>
  <a href="{PAGES_BASE}/web/sapphire.html">
    <img src="https://img.shields.io/badge/SERIES%205%20NET-{stats.get('sapphire', {'net':0})['net']:+.1f}u-2563EB?style=for-the-badge" alt="Series 5 Net" />
  </a>
  <a href="{PAGES_BASE}/web/quartz.html">
    <img src="https://img.shields.io/badge/SERIES%204%20NET-{stats.get('quartz', {'net':0})['net']:+.1f}u-f8fafc?style=for-the-badge" alt="Series 4 Net" />
  </a>

  <br />
  <br />
  <a href="{PAGES_BASE}/web/selector.html"><strong>ACCESS CONTROL CENTER</strong></a>
  <br />
  <br />
</div>

---

## ⚡ EXECUTIVE INTELLIGENCE

A multi-generational algorithmic trading system leveraging **Gradient Boosting Decision Trees (XGBoost)** and **Deep Neural Networks** to identify inefficiencies in sports betting markets.

| MODEL ARCHITECTURE | RELEASED | STRATEGY PROFILE | STATUS | VOLUME | TOTAL BETS | ROI |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **[SERIES 7: RUBY]({PAGES_BASE}/web/ruby.html)** | `AUG 27, 2026` | `FORWARD TEST` <br> Frozen walk-forward edge | 🔴 **ACTIVE** | Low (policy &le;6/day) | **{ruby_stats['sample']}** | **{ruby_roi_text}** |
| **[SERIES 6: KYANITE & CARNELIAN]({PAGES_BASE}/web/kyanite_carnelian.html)** | `MAY 16, 2026` | `SURGICAL ALPHA` <br> Precision/Yield | 💎 **ACTIVE** | {stats_v6['volume']} | **{stats_v6['sample']}** | **{stats_v6['roi']:+.1%}** |
{get_row('sapphire', 'SERIES 5: SAPPHIRE', 'MAY 13, 2026', 'CONFORMAL <br> Momentum', '🔵')}
{get_row('quartz', 'SERIES 4: QUARTZ', 'APR 06, 2026', 'INSTITUTIONAL <br> Drift Proxy', '⚪')}
{get_row('obsidian', 'SERIES 3: OBSIDIAN', 'DEC 27, 2025', 'ADVANCED ENSEMBLE <br> Non-Linear', '🟣')}
{get_row('diamond', 'SERIES 2: DIAMOND', 'NOV 30, 2025', 'PRECISION CORE <br> Refined', '🟢')}
{get_row('pyrite', 'SERIES 1: PYRITE', 'NOV 20, 2025', 'LEGACY CORE <br> High-Freq', '🟡')}

> [!IMPORTANT]
> **ACCESS PROTOCOL**: The primary interface for all models is the [**Model Selector**]({PAGES_BASE}/web/selector.html).

---

## 🛰 SYSTEMS OVERVIEW

### V7 RUBY // THE FORWARD TEST
*The honest edge.* Frozen policy from a leakage-controlled walk-forward, now live-tested from `AUG 27, 2026`.
*   **Protocol**: Policy grid tuned only on Nov 2025–May 2026 folds; frozen Jun–Aug untouched. Acceptance bar: t-stat ≥ 2, n ≥ 80, ≥ 2/3 months positive.
*   **Walk-forward result (frozen)**: n={ruby_stats['verification'].get('n', 307)}, ROI {ruby_stats['verification'].get('roi', 0.110):+.1%}, t-stat {ruby_stats['verification'].get('tstat', 2.04):+.2f}, {ruby_stats['verification'].get('profit', 33.8):+.1f}u, positive {ruby_stats['verification'].get('months_pos', '3/3')} months.
*   **Live tracking**: [Ruby Forward Ledger]({PAGES_BASE}/web/ruby.html) — updated daily by the pipeline, no retraining, no re-tuning.

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

*   **[SERIES 7: RUBY Audit](docs/reports/RUBY_REPORT.md)** - Frozen walk-forward results & forward-test protocol
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
    C -->|Forward| L[V7 RUBY]
    D & E & F & G & J & K & L -->|Simulate| H[DECISION SUPPORT]
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
            logger.info(f"📊 Total Rows in Data Lake: {len(raw_df)}")
            if len(raw_df) < 100000:
                 logger.error(f"❌ CRITICAL: Data lake row count ({len(raw_df)}) is below institutional threshold (100,000). Stats may be inaccurate.")
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
        ("carnelian", ms.run_Carnelian_carnelian),
        ("v6", ms.run_v6_sniper)
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
    
    # --- CALCULATE AGGREGATED STATS ---
    # [SURGICAL DNA]: Combined Series 6 Stats
    v6_list = [models.get('kyanite'), models.get('carnelian')]
    v6_list = [d for d in v6_list if d is not None and not d.empty]
    v6_df = pd.concat(v6_list) if v6_list else pd.DataFrame()
    stats_v6 = StatsEngine.calculate_metrics(v6_df)

    # 3. Generate Stats for JSON/JS
    # [A] STATS JSON GENERATION (Unified)
    stats_output = {
        "meta": {
            "last_update": et_now.strftime('%Y-%m-%d %H:%M ET'),
            "status": "NOMINAL",
            "cache_bust": et_now.timestamp()
        },
        "models": {}
    }

    # Standard Models
    for name in ['pyrite', 'diamond', 'obsidian', 'quartz', 'sapphire', 'v6']:
        df = models.get(name)
        if df is None or df.empty:
             stats_output["models"][name] = {"roi": 0.0, "net": 0.0, "wins": 0, "losses": 0, "pushes": 0, "record": "0-0-0", "win_rate": 0.0, "sample": 0, "bets_day": 0.0, "status": "ACTIVE", "yesterday": {"date": "N/A", "record": "0-0-0", "win_rate": 0, "net": 0, "roi": 0, "ledger": []}}
             continue

        m = StatsEngine.calculate_metrics(df)
        y = StatsEngine.get_yesterday_data(df, et_now=et_now)
        
        # Parse volume for bets_day float
        avg_bets = 0.0
        try:
             import re
             avg_match = re.search(r'~?(\d+)', m['volume'])
             if avg_match: avg_bets = float(avg_match.group(1))
        except:
             pass

        stats_output["models"][name] = {
            "roi": round(m['roi'] * 100, 1),
            "net": round(m['net'], 2),
            "wins": m['wins'],
            "losses": m['losses'],
            "pushes": m['pushes'],
            "record": m['record'],
            "win_rate": round(m['win_rate'] * 100, 1),
            "sample": m['sample'],
            "bets_day": avg_bets,
            "status": "ACTIVE",
            "yesterday": y if y else {"date": "N/A", "record": "0-0-0", "win_rate": 0, "net": 0, "roi": 0, "ledger": []}
        }

    # [SURGICAL DNA]: Institutional Mapping for 'Quarry Intelligence' (Zenith)
    stats_output["models"]["Quarry Intelligence"] = {
        "roi": round(stats_v6['roi'] * 100, 1),
        "net": round(stats_v6['net'], 2),
        "status": "INSTITUTIONAL"
    }
    # Add explicit kyanite/clv/carnelian for pages
    for m_name in ['kyanite', 'carnelian']:
        df = models.get(m_name)
        if df is not None:
            m = StatsEngine.calculate_metrics(df)
            stats_output["models"][m_name] = {"roi": round(m['roi']*100, 1), "net": round(m['net'], 2), "sample": m['sample'], "record": m['record']}

    # 4. Save Cache (Machine-Readable Summary)
    docs_dir = os.path.abspath(os.path.join(BASE_DIR, 'docs'))
    os.makedirs(docs_dir, exist_ok=True)
    
    # [BILLION DOLLAR OPTIMIZATION]: Cache results
    cache_path = os.path.join(docs_dir, 'sim_results_cache.pkl')
    try:
        joblib.dump(models, cache_path)
        logger.info(f"📦 Simulation results cached to {cache_path}")
    except Exception as e:
        logger.error(f"❌ Failed to cache results: {e}")
        
    # 4c. Export Machine-Readable Summary for GHA
    summary = {
        "last_update": et_now.strftime('%Y-%m-%d %H:%M ET'),
        "data_range": f"{raw_df['pick_date'].min().date()} to {raw_df['pick_date'].max().date()}" if not raw_df.empty else "N/A",
        "total_rows": len(raw_df),
        "picks_identified": {m: len(models[m]) for m in models}
    }
    with open(os.path.join(docs_dir, 'pipeline_summary.json'), 'w') as f:
        json.dump(summary, f, indent=4)
        
    # [HEARTBEAT]: Update heartbeat file ONLY on successful data processing
    with open(os.path.join(docs_dir, 'last_run.txt'), 'w') as f:
        f.write(f"Last successful run: {et_now.strftime('%a %b %d %H:%M:%S ET %Y')}")

    # 5. Update Markdown Reports
    try:
        update_markdown_reports(models)
    except Exception as e:
        logger.error(f"❌ Failed to update markdown reports: {e}")

    # 6/7. Assets (Plots, JSON, HTML Injection, Comparison) — weekly by default.
    # ASSETS_ENABLED is set by the workflow: daily runs skip asset regeneration
    # (saves ~1-2 min and stops daily PNG churn in git); the Monday run and
    # manual dispatches with force_assets=true rebuild everything.
    assets_enabled = os.environ.get("ASSETS_ENABLED", "false") == "true"
    if assets_enabled:
        logger.info("🎨 Generating Dashboard Assets (weekly refresh)...")
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
    else:
        logger.info("⏭️  Assets skipped (ASSETS_ENABLED=false) — ledger/stats still updated.")
    
    logger.info("✅ Daily Update Complete.")

if __name__ == "__main__":
    run_daily_update()
