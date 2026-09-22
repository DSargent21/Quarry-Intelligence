"""v8 JADE - exact CappersTracked grading.

Verified live against capperstracked.com/grading_system:
  R_hat = (n / (n + k)) * R_obs + (k / (n + k)) * mu_0,  k = 30, mu_0 = -5%
  - odds outside [-500, +350] american -> flat -110 (anomaly protection)
  - flat 1u staking
  - grades: A+ >= 8% | A >= 5% | B+ >= 3% | B >= 1% | C+ >= -1% | C >= -3% |
            D >= -5% | F < -5%; no grade below 5 graded picks.

With flat 1u staking this collapses to:  R_hat = (profit - 1.5u) / (n + 30)
Useful consequence: once a pick's expected profit is solidly positive, admitting
it RAISES the adjusted ROI (the +1 denominator costs ~1.5/(n+31) while the EV
gains more) - so for the grade, disciplined volume is nearly free. Volume is
controlled by the probability floor + daily cap, not by timid thresholds.
"""
import numpy as np
import pandas as pd

K = 30
MU0 = -0.05
ODDS_FLOOR, ODDS_CEIL = -500, 350
FLAT_DEC = 1.9091  # -110 american

GRADES = [
    (0.08, "A+"), (0.05, "A"), (0.03, "B+"), (0.01, "B"),
    (-0.01, "C+"), (-0.03, "C"), (-0.05, "D"), (-np.inf, "F"),
]


def grade_for(adj_roi):
    for thr, g in GRADES:
        if adj_roi >= thr:
            return g
    return "F"


def protected_dec_odds(d):
    """CappersTracked anomaly protection: odds outside [-500, +350] -> flat -110."""
    odds = d["odds_american"] if "odds_american" in d.columns else d["dec_odds"].apply(
        lambda dec: (dec - 1) * 100 if dec >= 2 else -100 / (dec - 1)
    )
    return np.where((odds >= ODDS_FLOOR) & (odds <= ODDS_CEIL), d["dec_odds"], FLAT_DEC)


def profit_vector(d):
    """Flat-1u profit for graded rows: win -> dec-1, loss -> -1. Pushes/pending excluded."""
    m = d["outcome"].isin([1.0, 0.0])
    dd = d[m]
    dec = protected_dec_odds(dd)
    y = dd["outcome"].values
    return y * (dec - 1) - (1 - y)


def grade_picks(df, stake_col=None):
    """Score a selection of picks exactly like CappersTracked.

    df must have 'outcome' (1/0, NaN for push/pending) and 'dec_odds'.
    Uses flat 1u staking.
    """
    d = df[df["outcome"].isin([1.0, 0.0])].copy()
    if d.empty:
        return {"n": 0, "grade": "-", "adj_roi": None, "roi": None,
                "profit": 0.0, "wr": None, "wins": 0, "losses": 0, "staked": 0.0}

    dec = protected_dec_odds(d)
    stake = np.ones(len(d)) if stake_col is None else d[stake_col].values
    y = d["outcome"].values
    profit = y * (dec - 1) * stake - (1 - y) * stake

    n = int(len(d))
    total_profit = float(profit.sum())
    total_staked = float(stake.sum())
    r_obs = total_profit / total_staked if total_staked > 0 else 0.0
    r_hat = (n / (n + K)) * r_obs + (K / (n + K)) * MU0

    return {
        "n": n,
        "wins": int(y.sum()),
        "losses": n - int(y.sum()),
        "wr": float(y.mean()),
        "profit": total_profit,
        "staked": total_staked,
        "roi": r_obs,
        "adj_roi": r_hat,
        "grade": grade_for(r_hat) if n >= 5 else "-",
    }


def concentration(d, top=1):
    """Share of total profit attributable to the top `top` cappers."""
    d = d[d["outcome"].isin([1.0, 0.0])]
    if d.empty:
        return float("nan")
    by = d.groupby("capper_id")["profit_1u"].sum()
    tot = by.sum()
    if tot <= 0:
        return float("nan")
    return float(by.nlargest(top).sum() / tot)
