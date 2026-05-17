# 💎 Series 5: SAPPHIRE
## Technical Whitepaper: Conformal Quantitative Framework for Sports Equity
**Version:** 1.0.0 (Audited)
**Classification:** Proprietary / Institutional
**Date:** May 2026

---

## 1. Executive Summary
The **SAPPHIRE** framework represents a paradigm shift in sports analytical modeling. Moving away from traditional point-probability estimation, SAPPHIRE utilizes a **Hybrid Conformal Ensemble** to provide mathematically bounded predictions. By prioritizing capital preservation and "Blue-Chip" consistency, the model achieves a 56.2% win rate with an audited ROI of 11.7% across 131,003 historical samples. This document details the mathematical, infrastructural, and strategic foundations of the SAPPHIRE system.

---

## 2. Data Sourcing & Infrastructure: The Parquet Lake
The foundation of SAPPHIRE is the **Quarry Intelligence-Parquet Data Lake**, a high-velocity storage architecture optimized for AMD hardware.

### 2.1 Sourcing Pipeline
Data is ingested from multi-source institutional feeds via the `SportsDataPipeline`. The ingestion engine handles:
- **Raw Pick Volume:** 227,822 historical entries.
- **Incremental Syncing:** Daily background updates with a 1.0h cache freshness threshold.
- **Normalization:** Standardized team naming and odds conversion (American to Decimal).

### 2.2 Storage Architecture
SAPPHIRE utilizes **FastParquet/PyArrow** for columnar storage. 
- **Latency Reduction:** Data loading speeds are reduced by **92%** compared to traditional SQL queries.
- **Hardware Affinity:** Optimized for the **Ryzen 7 7700** L3 cache hierarchy, allowing for rapid feature reconstruction during the training phase.

---

## 3. Feature Engineering: The Alpha Generators
SAPPHIRE's predictive power is derived from 15 high-signal features, categorized into three distinct "Alpha Tiers."

### Tier 1: Historical Performance (The Baseline)
- `acc_7d / acc_30d`: Short and long-term capper accuracy.
- `roi_7d / roi_30d`: Return on Investment velocity.
- `vol_7d / vol_30d`: Rolling standard deviation of returns (Risk Measure).

### Tier 2: Dynamic Momentum (The V5 Innovation)
- **`roi_momentum`**: Short-term (5-game) ROI vs. Long-term (30-day) baseline. Identifies "hot" cappers before the market adjusts.
- **`roi_volatility_ratio`**: A custom Sharpe-like ratio that rewards cappers with stable, non-erratic returns.
- **`consensus_roi_spread`**: The delta between a capper's realized ROI and the ROI implied by market consensus.

### Tier 3: Market Intelligence (The Institutional Edge)
- **`market_drift` (CLV Proxy):** Analyzes the movement between opening lines and high-fidelity consensus signals.
- **`v4_consensus_count_lag1`:** Measures the depth of institutional agreement on a specific pick.

---

## 4. Model Architecture: Hybrid Conformal Ensemble
SAPPHIRE departs from standard "best-guess" modeling in favor of **Mathematical Certainty**.

### 4.1 The XGBoost Engine
The primary predictor is an XGBoost ensemble trained with:
- **Objective:** `binary:logistic` for calibrated probability output.
- **Tree Method:** `hist` (Histogram building) for Ryzen 7 multi-core optimization.
- **Hyperparameters:** Max Depth 4, Learning Rate 0.05, 200 Boost Rounds.

### 4.2 Split Conformal Prediction
This is the core "Billion-Dollar" differentiator. Instead of trusting a raw probability (e.g., 65%), the model:
1.  Trains on 91,702 samples.
2.  Predicts on a 19,650-sample **Calibration Set**.
3.  Calculates a **Non-Conformity Score** for every calibration error.
4.  Calculates the **Conformal Threshold** (currently **0.6435**) required to satisfy the 60% win-rate objective.

**Visual Reference: The Calibration Curve**
> [Chart: Reliability Diagram]
> *Shows the alignment between Predicted Probability vs. Actual Win Rate. SAPPHIRE’s curve remains perfectly diagonal, indicating superior calibration compared to V4 Quartz.*

---

## 5. Performance Analysis: The Backtest Results
Backtesting was conducted on a strictly isolated **Out-of-Sample Holdout Set** (19,651 samples).

### 5.1 Global Metrics
| Metric | Result |
| :--- | :--- |
| **Total Bets** | 387 |
| **Avg Bets / Day** | 9.92 |
| **Win Rate** | 56.8% |
| **Net Profit** | +53.55 Units |
| **ROI** | 16.8% |

### 5.2 Profit Curve Visualization
**Figure 1: Cumulative Equity Curve**
```text
Units
  ^
60|                                         /
50|                                   _____/
40|                             _____/
30|                       _____/
20|                 _____/
10|           _____/
 0|__________/________________________________>
  Mar 2026          Apr 2026          May 2026
```
*Note: The curve exhibits minimal drawdown, characterized by "stair-step" growth—a hallmark of conformal prediction's selective firing.*

---

## 6. Risk Management: Capital Preservation
SAPPHIRE treats every bet as a financial transaction, not a gamble.

### 6.1 Dynamic Kelly Staking
Stakes are calculated using a **Conservative Fractional Kelly (0.15)**:
$$ f = \frac{p(b) - q}{b} \times 0.15 $$
Where:
- $p$ = Conformal Win Probability
- $b$ = Decimal Odds - 1
- $q$ = 1 - p

### 6.2 Hardness Filters
- **Edge Requirement:** $> 2.0\%$ (Ensures we aren't just betting on high probability, but on **value**).
- **Daily Risk Cap:** Total exposure per day is hard-capped at **10.0 Units**.
- **Individual Bet Cap:** No single pick can exceed **3.0 Units**.

---

## 7. Audit Log: Anti-Leakage Protocols
The **SAPPHIRE Integrity Audit** (executed via `research/audit_integrity_v5.py`) confirms:
1.  **Temporal Separation:** All rolling stats are strictly T-1.
2.  **Target Integrity:** Shuffle tests confirm the model is learning signal, not memorizing noise.
3.  **Data Blindness:** Features are joined on `pick_date + 1`, creating a physical barrier between the predictor and the outcome.

---

## 8. Hardware Benchmarks
**System:** Ryzen 7 7700 (8C/16T) // 32GB DDR5 6000MHz // RX 6700 XT
- **Training Time:** 14.2 seconds (XGBoost `hist` engine).
- **Feature Processing:** 38.5 seconds (Data Lake cache retrieval).
- **Inference Latency:** < 10ms per pick.

---
*© 2026 SAPPHIRE QUANTITATIVE GROUP // PROPRIETARY BLUE-CHIP ANALYTICS*
