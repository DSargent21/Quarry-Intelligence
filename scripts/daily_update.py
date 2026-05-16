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
from models import ModelSimulator
from src.utils.logger import logger
from src.utils.validator import DataValidator

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
    """Ported from monitor.py: Updates README.md and LATEST_ACTION.md with latest results."""
    logger.info("📝 Updating System Reports (README.md & LATEST_ACTION.md)...")
    
    # --- HELPER FUNCTIONS ---
    def get_stats(d):
        if d is None or d.empty: return 0.0, 0.0, 0.0
        settled = d[d['outcome'].isin([0.0, 1.0])]
        if settled.empty: return 0.0, 0.0, 0.0
        p = settled['profit_actual'].sum()
        r = settled['wager_unit'].sum()
        roi = p/r if r>0 else 0.0
        wr = len(settled[settled['outcome']==1]) / len(settled)
        return p, roi, wr

    def get_volume_text(d):
        if d is None or d.empty: return "None (0 bets/day)"
        days = (d['pick_date'].max() - d['pick_date'].min()).days + 1
        avg = len(d) / max(days, 1)
        if avg > 50: cat = "Very High"
        elif avg > 20: cat = "High"
        elif avg > 10: cat = "Medium"
        elif avg > 5: cat = "Low"
        else: cat = "Very Low"
        return f"{cat} (~{int(avg)} bets/day)"

    # --- CALCULATE STATS ---
    v1, v2, v3, v4, v5 = models.get("pyrite"), models.get("diamond"), models.get("obsidian"), models.get("quartz"), models.get("sapphire")
    p1, r1, w1 = get_stats(v1)
    p2, r2, w2 = get_stats(v2)
    p3, r3, w3 = get_stats(v3)
    p4, r4, w4 = get_stats(v4)
    p5, r5, w5 = get_stats(v5)
    
    vol_v1 = get_volume_text(v1)
    vol_v2 = get_volume_text(v2)
    vol_v3 = get_volume_text(v3)
    vol_v4 = get_volume_text(v4)
    vol_v5 = get_volume_text(v5)

    # --- 1. LATEST_ACTION.md ---
    dates = []
    for d in [v1, v2, v3, v4, v5]:
        if d is not None and not d.empty: dates.append(d['pick_date'].max())
    
    last_date = max(dates) if dates else datetime.now()
    
    log_content = f"# 📝 Daily Action Log ({last_date.date()})\n\n"
    
    def make_table(df, title):
        if df is None or df.empty: return ""
        t = f"### {title}\n"
        t += "| LEAGUE | PICK | ODDS | UNIT | RES | PROFIT |\n"
        t += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        day_df = df[df['pick_date'] == last_date]
        if day_df.empty: return f"### {title}\n*No action for this date.*\n\n"
        
        for _, row in day_df.iterrows():
            res = "✅" if row['outcome'] == 1.0 else "❌" if row['outcome'] == 0.0 else "⏳"
            odds = row.get('decimal_odds', row.get('odds_american', 0))
            if 'odds_american' in row and row['odds_american'] != 0:
                odds_text = f"+{int(row['odds_american'])}" if row['odds_american'] > 0 else f"{int(row['odds_american'])}"
            else:
                odds_text = f"{odds:.2f}"
                
            t += f"| {row['league_name']} | {row.get('pick_norm', row.get('pick_value', 'N/A'))} | {odds_text} | {row['wager_unit']:.1f} | {res} | {row['profit_actual']:+.2f}u |\n"
        
        daily_profit = day_df[day_df['outcome'].isin([0.0, 1.0])]['profit_actual'].sum()
        t += f"\n**Daily PnL (Settled): {daily_profit:+.2f} Units**\n\n"
        return t + "\n"

    log_content += make_table(v5, "V5 Sapphire Action")
    log_content += make_table(v4, "V4 Quartz Action")
    log_content += make_table(v3, "V3 Obsidian Action")
    log_content += make_table(v2, "V2 Diamond Action")
    log_content += make_table(v1, "V1 Pyrite Action")
    
    with open(os.path.join(BASE_DIR, "LATEST_ACTION.md"), "w", encoding="utf-8") as f:
        f.write(log_content)

    # --- 2. README.md ---
    readme_text = f"""
<div align="center">
  <br />
  <h1>QUARRY INTELLIGENCE</h1>
  <p style="font-family: monospace; letter-spacing: 2px; color: #888;">INSTITUTIONAL ALGORITHMIC ANALYTICS</p>
  <br />

  [![Status](https://img.shields.io/badge/STATUS-OPERATIONAL-success?style=for-the-badge&logo=statuspage&logoColor=white)](https://ducky705.github.io/Quarry-Intelligence/selector.html)
  [![Series 5 ROI](https://img.shields.io/badge/SERIES_5_ROI-{p5:+.1f}u-2563EB?style=for-the-badge)](https://ducky705.github.io/Quarry-Intelligence/sapphire.html)
  [![Series 4 ROI](https://img.shields.io/badge/SERIES_4_ROI-{p4:+.1f}u-f8fafc?style=for-the-badge)](https://ducky705.github.io/Quarry-Intelligence/quartz.html)

  <br />
  <br />
  <a href="https://ducky705.github.io/Quarry-Intelligence/selector.html"><strong>ACCESS CONTROL CENTER</strong></a>
  <br />
  <br />
</div>

---

## ⚡ EXECUTIVE INTELLIGENCE

A multi-generational algorithmic trading system leveraging **Gradient Boosting Decision Trees (XGBoost)** and **Deep Neural Networks** to identify inefficiencies in sports betting markets.

| MODEL ARCHITECTURE | RELEASED | STRATEGY PROFILE | STATUS | VOLUME | TOTAL BETS | ROI |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **[SERIES 1: PYRITE](https://ducky705.github.io/Quarry-Intelligence/pyrite.html)** | `NOV 20, 2025` | `LEGACY CORE` <br> High-Freq | 🟡 **LEGACY** | {vol_v1} | **{len(v1)}** | **{r1:+.1%}** |
| **[SERIES 2: DIAMOND](https://ducky705.github.io/Quarry-Intelligence/diamond.html)** | `NOV 30, 2025` | `PRECISION CORE` <br> Refined | 🟢 **STABLE** | {vol_v2} | **{len(v2)}** | **{r2:+.1%}** |
| **[SERIES 3: OBSIDIAN](https://ducky705.github.io/Quarry-Intelligence/obsidian.html)** | `DEC 27, 2025` | `ADVANCED ENSEMBLE` <br> Non-Linear | 🟣 **ADVANCED** | {vol_v3} | **{len(v3)}** | **{r3:+.1%}** |
| **[SERIES 4: QUARTZ](https://ducky705.github.io/Quarry-Intelligence/quartz.html)** | `APR 06, 2026` | `INSTITUTIONAL` <br> Drift Proxy | ⚪ **FLAGSHIP** | {vol_v4} | **{len(v4)}** | **{r4:+.1%}** |
| **[SERIES 5: SAPPHIRE](https://ducky705.github.io/Quarry-Intelligence/sapphire.html)** | `MAY 13, 2026` | `CONFORMAL` <br> Momentum | 🔵 **PREMIUM** | {vol_v5} | **{len(v5) if v5 is not None else 0}** | **{r5:+.1%}** |

> [!IMPORTANT]
\> **ACCESS PROTOCOL**: The primary interface for all models is the [**Model Selector**](https://ducky705.github.io/Quarry-Intelligence/selector.html).

---

## 🛰 SYSTEMS OVERVIEW

### V5 SAPPHIRE // THE CONFORMAL ENGINE
*The definitive shift.* Employs **Split Conformal Prediction** and **Dynamic Momentum** to bound risk and capture institutional-grade win thresholds.
*   **Mechanism**: Asymmetric loss optimization with drift-aware feature engineering.
*   **Performance**: Targeting maximum precision and high-fidelity alpha.

### V4 QUARTZ // THE PRISM
*The flagship standard.* Utilizes **Correct Shift** logic to identify opening line inefficiencies.

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
    D & E & F & G & J -->|Simulate| H[DECISION SUPPORT]
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
    
    # Wrap each model run in a try-except to prevent one failure from killing the pipeline
    simulation_tasks = [
        ("pyrite", ms.run_v1_pyrite),
        ("diamond", ms.run_v2_diamond),
        ("obsidian", ms.run_v3_obsidian),
        ("quartz", ms.run_v4_quartz),
        ("sapphire", ms.run_v5_sapphire)
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
    stats = {
        "meta": {
            "last_update": datetime.now(pd.Timestamp.now(tz='UTC').tz).strftime('%Y-%m-%d %H:%M UTC'),
            "status": "NOMINAL"
        },
        "models": {}
    }
    
    for name, res in models.items():
        if res is None or res.empty or 'profit_actual' not in res.columns:
            stats["models"][name] = {
                "roi": 0, "net": 0, "wins": 0, "losses": 0, "pushes": 0,
                "record": "0-0-0", "win_rate": 0, "sample": 0, "bets_day": 0,
                "status": "OFFLINE",
                "yesterday": {"date": "N/A", "record": "0-0-0", "net": 0, "roi": 0, "ledger": []}
            }
        else:
            # [STABILITY FIX]: Check if wager_unit sum is 0
            wager_total = res['wager_unit'].sum()
            roi = (res['profit_actual'].sum() / wager_total * 100) if wager_total > 0 else 0
            net = res['profit_actual'].sum()
            wins = len(res[res['outcome'] == 1])
            losses = len(res[res['outcome'] == 0])
            pushes = len(res[res['outcome'] == 0.5])
            
            # [CRASH PREVENTION]: Ensure pick_date exists and is not empty
            if 'pick_date' in res.columns and not res['pick_date'].isnull().all():
                last_day_val = res['pick_date'].max()
                last_day = res[res['pick_date'] == last_day_val]
            else:
                last_day_val = datetime.now()
                last_day = pd.DataFrame()
                
            y_record = "0-0-0"
            y_net = 0
            y_roi = 0
            y_winrate = 0
            y_list = []
            
            if not last_day.empty:
                y_wins = len(last_day[last_day['outcome'] == 1])
                y_losses = len(last_day[last_day['outcome'] == 0])
                y_record = f"{y_wins}-{y_losses}-{len(last_day) - y_wins - y_losses}"
                y_net = last_day['profit_actual'].sum()
                y_roi = (y_net / last_day['wager_unit'].sum() * 100) if last_day['wager_unit'].sum() > 0 else 0
                y_winrate = (y_wins / (y_wins + y_losses) * 100) if (y_wins + y_losses) > 0 else 0
                
                # Ensure columns are unique before converting to dict (Prevents UserWarning & data loss)
                last_day_unique = last_day.loc[:, ~last_day.columns.duplicated()]
                y_list = last_day_unique.sort_values('profit_actual', ascending=False).head(15).to_dict('records')
                for item in y_list:
                    item['pick_date'] = item['pick_date'].strftime('%m/%d')
                    item['result'] = 'WIN' if item['outcome'] == 1 else ('LOSS' if item['outcome'] == 0 else 'PUSH')
                    for k in list(item.keys()):
                        if k not in ['pick_date', 'league_name', 'pick_norm', 'decimal_odds', 'wager_unit', 'result', 'profit_actual', 'edge']:
                            del item[k]

            stats["models"][name] = {
                "roi": round(roi, 1),
                "net": round(net, 1),
                "wins": wins,
                "losses": losses,
                "pushes": pushes,
                "record": f"{wins}-{losses}-{pushes}",
                "win_rate": round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0,
                "sample": len(res),
                "bets_day": round(len(res) / (max((res['pick_date'].max() - res['pick_date'].min()).days, 0) + 1), 1) if not res.empty else 0,
                "status": "LEGACY" if name == "pyrite" else ("STABLE" if name == "diamond" else ("ADVANCED" if name == "obsidian" else ("FLAGSHIP" if name == "quartz" else "PREMIUM"))),
                "yesterday": {
                    "date": last_day_val.strftime('%b %d, %Y') if hasattr(last_day_val, 'strftime') else "N/A",
                    "record": y_record,
                    "win_rate": round(y_winrate, 1),
                    "net": round(y_net, 2),
                    "roi": round(y_roi, 1),
                    "ledger": y_list
                }
            }

    # Final Stats Validation
    if not DataValidator.validate_stats_json(stats):
        logger.warning("⚠️ Final stats failed validation. Proceeding with caution.")

    # 4. Save Stats
    docs_dir = os.path.join(BASE_DIR, 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    
    with open(os.path.join(docs_dir, 'stats.json'), 'w') as f:
        json.dump(stats, f, indent=4)
        
    with open(os.path.join(docs_dir, 'stats.js'), 'w') as f:
        f.write(f"window.QUARRY_STATS = {json.dumps(stats, indent=4)};")
        
    # [BILLION DOLLAR OPTIMIZATION]: Cache results
    cache_path = os.path.join(docs_dir, 'sim_results_cache.pkl')
    try:
        joblib.dump(models, cache_path)
        logger.info(f"📦 Simulation results cached to {cache_path}")
    except Exception as e:
        logger.error(f"❌ Failed to cache results: {e}")
        
    # 4c. Export Machine-Readable Summary for GHA
    summary = {
        "last_update": stats['meta']['last_update'],
        "data_range": f"{raw_df['pick_date'].min().date()} to {raw_df['pick_date'].max().date()}" if not raw_df.empty else "N/A",
        "total_rows": len(raw_df),
        "picks_identified": {m: len(models[m]) for m in models}
    }
    with open('docs/pipeline_summary.json', 'w') as f:
        json.dump(summary, f, indent=4)
        
    # 5. Update Markdown Reports
    try:
        update_markdown_reports(models)
    except Exception as e:
        logger.error(f"❌ Failed to update markdown reports: {e}")

    # 6. Generate Assets (Plots & HTML Injection)
    logger.info("🎨 Generating Assets...")
    try:
        import scripts.generate_assets as generate_assets
        generate_assets.generate_live_assets()
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
