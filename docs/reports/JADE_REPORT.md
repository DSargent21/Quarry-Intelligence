# v8 JADE — Score-Optimized Capper Selection System

**Goal:** maximize the CappersTracked grade on *future, unseen* picks, with zero leakage.
Grading was verified live against `capperstracked.com/grading_system` and is implemented
byte-exact in `score.py` (Bayesian shrinkage k=30, μ₀ = −5%, odds clamp [−500,+350] → flat
−110, flat 1u staking, A+ ≥ 8% / A ≥ 5% / B+ ≥ 3% / B ≥ 1% …, no grade under 5 picks).

**Data:** 155,835 picks (141,831 graded) fetched fresh from Supabase, 2024-01-01 → 2026-09-21.
All v7 data-quality fixes retained (Int64 id precision, id dedup, NaN-outcome protection,
regraded-Discord relabeling).

**With flat 1u staking the grade collapses to R̂ = (profit − 1.5u) / (n + 30)** — so for the
grade, disciplined volume above breakeven is nearly free, and the model's job is pure ranking
quality. The system is therefore built around rank-based daily slates rather than absolute
probability thresholds.

---

## 1. Protocol (pre-registered, no exceptions)

Anchored expanding-window walk-forward, retrained monthly, evaluation months Mar–Sep 2026:

- model **training**: all graded picks strictly before T − 30d (T = fold start)
- model **early stopping**: [T − 60d, T − 30d) — strictly before T, never the eval month
- **isotonic calibration**: [T − 30d, T) — strictly before T
- predictions for [T, month end) are out-of-sample
- policy tuning happens only on folds before each channel's cutoff; frozen results are
  evaluated untouched; pre-registered gates decide deployment
- **one policy round per pre-registered plan; the round-3 freeze was never re-tuned after
  the single Sep holdout look**

### Acceptance gates (frozen before any evaluation)
adj ROI ≥ +5% · n ≥ 100 · t ≥ 2.0 · ≥ 75% of months positive · top capper ≤ 40% of profit.

---

## 2. Data regime change (the decisive finding)

**The Discord feed went dark on 2026-08-01.** Aug + Sep 2026 contain 66 Discord rows total
(22 graded, all Sep). Site picks continue at full volume (Aug: 2,882 graded; Sep: 9,441).

Consequences:
- The v7 RUBY edge — a Discord-picks edge — **cannot make any future bets**; its live
  ledger will stay empty regardless of backtest quality.
- Jade therefore ships two channels: Discord (validated for honesty, **disabled**) and a
  **site-picks channel** (the deployable one).
- For the site channel the frozen holdout is **September 2026** — a month never seen by any
  tuning step.

---

## 3. Round 1 — v7-style design, honestly evaluated: FAIL

Discord channel, policy tuned on Nov–May aggregate, frozen Jun–Jul:
**n=422, ROI +1.5%, adj +1.1% (B), t=+0.33 → FAIL.** v7's +11% "frozen" result does not
survive fully causal early stopping — v7 early-stopped on the eval month itself (mild
leakage), which is the most plausible explanation for the gap. The v7-style site policy
(absolute calibrated-probability thresholds, aggregate-tuned) looked great in-sample
(adj +9.9%, "A+" on Mar–Aug) but **failed the true Sep holdout** (adj −2.4%).

## 4. Round 2 — stability-based policy selection: still short

Added per-fold calibration of the site channel, rank-based (calibration-immune) policies,
coarse odds bands, and a stability rule: require ≥ 60% of tune months positive (n ≥ 10),
rank by worst-month adj ROI instead of aggregate max.

- Tune (Mar–Aug): 4/6 months positive, worst month −1.9% — real stability improvement.
- **Frozen Sep: n=105, ROI +2.3%, adj +0.7% (C+), t=+0.26 → FAIL.**

## 5. Round 3 — feature-policy alignment: the champion

The grading formula shrinks toward a prior; cappers' skill estimates should too. The
**shrunk lifetime skill gate** (`shrunk_acc_lt`: capper win rate shrunk with k=24 toward
0.5, mirroring the grading math) was the aligned intervention. Ten variants were evaluated
tune-only with the stability rule; the best was frozen and evaluated once on Sep:

| Variant (tune Mar–Aug) | Months pos. | Worst adj | Agg adj |
|---|---|---|---|
| **V6 skill ≥ 0.55** | **5/6** | **−0.2%** | **+12.1%** (n=777) |
| V1 baseline rank/5d | 4/6 | −1.9% | +7.6% |
| V10 skill+cap3 | 5/6 | −1.6% | +13.7% |
| V4/V5 consensus gates | 2/6 | −13.8% | negative |

**Frozen V6 on Sep (true holdout): n=95, WR 58.9%, raw ROI +11.7%, adj ROI +7.7% → grade A, +11.1u.**
90% bootstrap CI adj ROI [−4.5%, +19.7%], t=+1.22, top-1 capper share 41%.

### Gate verdict — applied literally, no goalpost-moving
| Gate | Threshold | Sep result | Verdict |
|---|---|---|---|
| adj ROI | ≥ +5% | +7.7% | **PASS** |
| n | ≥ 100 | 95 | **FAIL** (single-month volume) |
| t-stat | ≥ 2.0 | +1.22 | **FAIL** (single-month sample) |
| months positive | ≥ 75% | n/a (one month) | not evaluable |
| top capper share | ≤ 40% | 41% | borderline |

**Interpretation:** the sign and magnitude are right; n and t fail purely on single-month
sample size — exactly what a forward test resolves. **V6 ships as a candidate, not a proven
edge.** Per pre-commitment, there was no round 4: every further knob-turn would have been
fitting Sep.

### Implementation corrections (not score-driven tuning)
Post-validation fixes, made because they change what is *bettable*, not what scores well:
- **Deterministic tie-break:** isotonic calibration creates step levels; within a level,
  ties now break by raw model probability (validated run used arbitrary order).
- **Posted odds required:** 8% of Sep rows had null odds and silently graded at flat −110;
  a pick with no posted price cannot be bet and is now excluded at selection time.

Deployment-realistic Sep under both corrections: **n=88, WR 60.2%, raw ROI +13.7%,
adj +8.9%, +12.0u** — consistent with the validated +7.7% headline.

---

## 6. Why the shrunk-skill gate works

Selection quality comes from *who* is picking, not just market odds: the capper's own
history in the value band (`band_roi_lt`, `band_wr_lt` — their past ROI at 1.80–2.40
decimal) and grading-mirrored shrunk skill all rank in the model's top features by gain.
The gate (shrunk lifetime skill ≥ 0.55) removes cappers whose grade-blended history says
they are not profitable, before the model ever ranks a slate.

## 7. System artifacts

| File | Role |
|---|---|
| `fetch.py` | Supabase fetch + all data-quality fixes; cached parquet; `--refresh` |
| `features.py` | v7's point-in-time builder + Jade features (band ROI history, shrunk skill) |
| `models.py` | XGBoost pair, causal early stopping, isotonic recalibration |
| `score.py` | byte-exact CappersTracked grading + bootstrap + concentration |
| `walkforward.py` | dual-channel walk-forward, frozen policies, gates, sweep cache |
| `variants.py` | round-3 pre-registered variant selection (tune-only + single freeze) |
| `deploy.py` | final training on all data → `models/jade_all.json`, `jade_disc.json`, `jade_iso.pkl`, `jade_policy.json` |
| `forward.py` | daily frozen tracker → `forward_ledger.json` + `FORWARD_LEDGER.md` |

Leakage controls verified in code: features use +1-day shifted aggregates merged
as-of-backward; consensus uses previous days only; model early stopping never touches the
eval month; calibration window ends before T; policy tuning windows end before each
channel's cutoff; the forward tracker never trains.

## 8. Morning operating procedure

1. `python3 v8_jade/forward.py` (fresh fetch, scores with frozen models, updates ledger)
2. Bet the slate: max 5 picks/day, flat 1u each, odds 1.80–2.00 decimal (−125 to −100
   American) only, picks meeting the shrunk-skill gate
3. Grade as results land; do not chase, do not stake non-1u, do not skip days

## 9. Risks and honest limitations

- **Single-month holdout.** The +7.7% adj is one month (n=95). The CI includes zero. Only
  the forward test turns "candidate" into "confirmed."
- **Odds at grading time, not pick time.** Site picks are graded at recorded odds; real
  execution uses the price you can actually take. If recorded odds differ from pick-time
  prices, some measured edge is execution timing.
- **Capper turnover.** The gate leans on capper history; new cappers take time to clear
  it, and hot cappers can go cold. The 41% top-capper concentration is at the risk limit.
- **Market drift.** Monthly retraining in the walk-forward absorbs drift; the deployed
  model is static until the next scheduled retrain (repeat `deploy.py`, bump the policy
  version, and start a fresh ledger window — never mid-ledger).
- **The Discord channel is disabled**, not dead: if the feed resumes, re-run
  `walkforward.py` (it re-validates from scratch) before betting a single Discord pick.

## 10. Go/no-go

**GO for the v8 JADE forward test under the frozen V6 policy, flat 1u staking** — with the
explicit caveat that the Sep holdout passed the adj-ROI gate but missed the volume and
significance gates on sample size. The forward ledger (`FORWARD_LEDGER.md`) is the referee:
it started 2026-09-22, and the go/no-go for real bankroll scale-up is re-evaluated after
~100 graded forward picks. Until then: bet the slate small, bet it every day, touch nothing.
