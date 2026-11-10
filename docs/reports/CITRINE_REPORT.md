# v9 CITRINE — Skill-Gated ML Blend (Series IX)

**Goal:** a higher-volume successor to the Ruby/Jade design that keeps a leakage-free,
walk-forward-verified edge while betting roughly 8 picks a day instead of 5.

Series IX is deliberately a **forward-first** system: the published page opens on an empty
ledger because a backtest is not a track record. Numbers below are out-of-sample evidence
that justify *starting* the live test — not a promise of profit.

---

## 1. Question this model answers

Earlier series found two separate sources of signal:

| Source | What it captured | Weakness |
| --- | --- | --- |
| Capper skill (shrunk, grading-mirrored) | *who* is picking | goes stale, hot streaks regress |
| ML ranking (XGBoost pair on point-in-time features) | *price vs probability* | thin at low volume, noisy at high volume |

Citrine blends them and then applies a **skill gate** before the model ever ranks a slate.
The blend raises volume without letting the model bet on cappers whose own history says they
are unprofitable.

**The hypothesis that failed.** "Tail hot form, fade cold form" — the starting idea — does
not survive honest testing. Recent-form features rank low by gain, and a pure form-only
policy is negative out-of-sample. Form is a *weak* conditioner inside the blend, not an edge
on its own.

---

## 2. Leakage controls (verified in code)

Every control below is enforced in the builder/runner, not by convention:

- **Feature lag.** All aggregate features (capper ROI, band ROI, volume, win rate) are
  computed on a `+1 day` shifted frame and merged `as-of backward`, so a pick can never see
  a result that settled on the same day or later.
- **Early stopping inside the training window.** Validation slice ends strictly before the
  fold start; the evaluation month is never touched by stopping or calibration.
- **Pre-fold calibration.** Isotonic recalibration is fit on the 30 days immediately before
  the fold, never on the fold itself.
- **Result lag.** Outcomes enter the feature store 3 days after the pick date.
- **Frozen policy.** Thresholds, odds band and daily cap are chosen on folds before the
  cutoff and then frozen; the out-of-sample window is evaluated once.
- **Posted price required.** A selection with no posted odds is excluded — it cannot be bet,
  and grading it at a synthetic −110 inflates ROI.
- **No duplicate ids.** Re-inserted rows are deduped by latest `created_at`.
- **Cluster-aware inference.** Confidence intervals are bootstrap-resampled **by day**
  (picks on the same slate are correlated), not by pick.

---

## 3. Out-of-sample result (Apr–Sep 2026)

Policy: skill gate, blend of the all-picks and Discord-channel models, **top 8 per day**,
flat 1u, decimal odds 1.85–2.20.

| Metric | Value |
| --- | --- |
| Window | 2026-04-01 → 2026-09-22 |
| Selections graded | 1,126 |
| Win rate | 56.0% |
| Raw ROI | +6.21% |
| Adjusted ROI (skill) | **+5.92%** |
| Profit | +70.0u |
| t-statistic | +2.21 |
| 90% day-clustered CI | [+1.48%, +10.38%] |

The interval excludes zero at 90%, but not comfortably. September alone (n=165) is
+5.19% adjusted with a t of +0.97 and a CI that crosses zero — the most recent month is the
weakest evidence, which is exactly why the live ledger outranks this table.

**Baseline for scale.** The same 1.80–2.00 band across the whole book (n=65,939) wins 49.9%
at a raw ROI of −5.19%. Citrine's selection is therefore ~11 points of win rate and ~11
points of ROI above the population it draws from.

---

## 4. The volume trade-off (why 8/day)

| Daily cap | Selections | Adjusted ROI |
| --- | --- | --- |
| 5 | 730 | +8.07% |
| **8** | **1,126** | **+5.92%** |
| 10 | 1,362 | +5.06% |
| 15 | — | +3.98% |
| 20 | — | +1.99% |

Edge decays monotonically with volume: past ~8 selections the model is filling slots with
picks it does not actually like. 5/day is the highest quality but too thin to distinguish
skill from luck in a season; **8/day is the volume sweet spot** and is the frozen policy.

---

## 5. Forward-test protocol

1. **Freeze** up to eight selections before the slate locks — nothing is added afterwards.
2. **Grade** at the posted price only. No later edits, no line shopping, no CLV adjustment
   (these markets have no reliable closing line to measure against).
3. **Update** the ledger, ROI, drawdown and capper concentration after every graded day.
4. **Judge** on forward picks alone. The backtest never gets a vote on whether Citrine works.

Acceptance (pre-registered, same bar as Ruby/Jade): adjusted ROI ≥ +5%, n ≥ 100,
t ≥ 2.0, majority of months positive, top capper ≤ 40% of profit. Until then the page shows
a zero ledger — by design, not by omission.

---

## 6. Artifacts

| Path | Role |
| --- | --- |
| `v14_final/model.py` | walk-forward blend, calibration, cluster CIs, volume sweep |
| `v14_final/oos_predictions.parquet` | out-of-sample predictions used for every figure |
| `v14_final/make_pngs.py` | equity, monthly, reliability and volume charts |
| `v10_advanced/V10_FINDINGS.md` | full research log: what failed, what survived |
| `docs/web/citrine.html` | forward-first tracker (grid, ledger, validation) |
| `docs/web/citrine_summary.json` | machine-readable OOS + forward summary |

Charts embedded on the page: equity curve, monthly adjusted ROI, reliability curve,
volume comparison.

---

## 7. Risks and honest limits

- **One evaluation window.** Six months of out-of-sample picks is one regime. The CI lower
  bound (+1.5%) is thin relative to the headline.
- **Execution gap.** Graded at recorded posted odds; a real bettor taking a worse price
  gives up part of the measured edge.
- **Blend opacity.** Two models averaged 50/50 is a deliberate simplification, not an
  optimised ensemble; it was chosen before evaluation and not re-tuned afterwards.
- **No forward record yet.** Citrine is a candidate. Treat the 0-graded ledger as the honest
  state of the system.
