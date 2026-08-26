"""Exact CappersTracked grading: Bayesian-shrinkage adjusted ROI -> letter grade.

Formula: R_hat = (n / (n + k)) * R_obs + (k / (n + k)) * mu_0
with k = 30, mu_0 = -5%, and anomaly protection:
  - odds outside [-500, +350] american are replaced with flat -110
  - (unit outliers are irrelevant here because we stake flat 1u)

Grades (adjusted ROI):
  A+ >= 8% | A >= 5% | B+ >= 3% | B >= 1% | C+ >= -1% | C >= -3% | D >= -5% | F < -5%
No grade below 5 graded picks.
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


def grade_picks(df, stake_col=None):
    """Score a selection of picks exactly like CappersTracked.

    df must have 'outcome' (1/0) and 'dec_odds'. Uses flat 1u staking.
    Returns dict with n, record, win rate, raw ROI, protected ROI, adjusted ROI, grade.
    """
    d = df[df["outcome"].isin([1.0, 0.0])].copy()
    if d.empty:
        return {"n": 0, "grade": "-", "adj_roi": None, "roi": None, "profit": 0.0, "wr": None}

    # Anomaly protection: clamp extreme odds to flat -110
    odds = d["odds_american"] if "odds_american" in d.columns else d["dec_odds"].apply(
        lambda dec: (dec - 1) * 100 if dec >= 2 else -100 / (dec - 1)
    )
    protected_dec = np.where(
        (odds >= ODDS_FLOOR) & (odds <= ODDS_CEIL), d["dec_odds"], FLAT_DEC
    )
    stake = np.ones(len(d)) if stake_col is None else d[stake_col].values
    profit = d["outcome"].values * (protected_dec - 1) * stake - (1 - d["outcome"].values) * stake

    n = int(len(d))
    total_profit = float(profit.sum())
    total_staked = float(stake.sum())
    r_obs = total_profit / total_staked if total_staked > 0 else 0.0
    r_hat = (n / (n + K)) * r_obs + (K / (n + K)) * MU0
    wr = float(d["outcome"].mean())

    return {
        "n": n,
        "wins": int(d["outcome"].sum()),
        "losses": n - int(d["outcome"].sum()),
        "wr": wr,
        "profit": total_profit,
        "staked": total_staked,
        "roi": r_obs,
        "adj_roi": r_hat,
        "grade": grade_for(r_hat) if n >= 5 else "-",
    }
