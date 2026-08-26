# v7 RUBY - Walk-Forward Results (honest out-of-sample)

Data: 131071 graded picks | 9 monthly folds Nov 2025-Aug 2026, model retrained per fold strictly point-in-time.
No leakage: each fold's model sees only picks strictly before that month.

## Protocol (pre-registered)
- Policy grid (216 configs) tuned ONLY on folds before 2026-06-01 (Nov-May).
- Frozen on 2026-06-01 onward (Jun, Jul, Aug) - untouched during tuning.
- Acceptance bar: frozen t-stat >= 2, n >= 80, >= 2/3 months positive.

## Verdict: **real edge found, borderline significant**

Frozen Jun-Aug: **n=307, ROI +11.0%, t-stat +2.04, profit +33.8u, positive 3/3 months**.

Per month (frozen):
- 2026-06: n=121 WR=53.7% ROI=+3.0% profit=+3.7u
- 2026-07: n=137 WR=62.8% ROI=+20.1% profit=+27.6u
- 2026-08: n=49 WR=55.1% ROI=+5.1% profit=+2.5u

## Tuning window (Nov-May, same config)
n=305, adj ROI 6.6%, t-stat +1.43 (consistent sign - not a lucky single month).

## Baselines (Jun-Aug, same window)
- All Discord: n=11177 roi=-3.1%
- Top-prob 50/day: n=3117 roi=-3.0%

## Why the edge exists
- Selections beat the posted line: mean model prob 0.591, mean implied 0.523, actual WR 0.580.
- Odds window [1.85, 2.20] mid-range favorites; WR ~58% vs ~52% breakeven.
- Market as a whole loses ~3% (the vig); the model's selection is +13-14pts above baseline.

## Known risks
- Concentration: top capper (Nickycashin) = +16.7u of +33.8u (~50%). Excluding them: n=270, ROI +6.3% - still positive, weaker.
- t-stat 2.04 is borderline (p~0.04 two-sided); multiple configs were tried, though the whole neighborhood (min_prob/edge) is positive on frozen months.
- Graded vs posted odds at pick time, not closing lines; edge may be partly CLV and can fade.
- Final confirmation = September forward test, policy frozen.

## Policy
- Discord only | prob >= 0.56 | edge >= 0.01 | dec odds [1.85, 2.2]
- capper >= 3 picks/30d | max 6/day
