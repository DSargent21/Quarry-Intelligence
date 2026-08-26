"""v7 RUBY - Discord-first score-maximizing sniper.

Pipeline: fetch -> features -> chronological split -> XGBoost -> threshold/selection
tuning on validation to maximize CappersTracked Bayesian adjusted ROI -> frozen
evaluation on test.

Usage: python3 v7_ruby/run.py
"""
import os
import sys
import json
import itertools
import numpy as np
import pandas as pd
import xgboost as xgb
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from fetch import load_data
from features import build_features
from score import grade_picks, grade_for

load_dotenv()

BASE = os.path.dirname(os.path.abspath(__file__))

TRAIN_END = "2026-03-31"
VAL1_END = "2026-05-31"   # tune here
VAL2_END = "2026-06-30"   # pick by generalization here
TEST_END = "2099-12-31"

NUMERIC_FEATURES = [
    "acc_7d", "acc_14d", "acc_30d", "acc_60d", "acc_90d",
    "roi_7d", "roi_14d", "roi_30d", "roi_60d", "roi_90d",
    "vol_30d", "vol_90d", "cnt_7d", "cnt_30d", "cnt_90d",
    "roi_vol_ratio_30d", "sharpe_30d", "acc_mom_7_30", "acc_mom_14_60", "roi_per_pick_30d",
    "lt_cnt", "lt_roi", "lt_acc",
    "d_roi_7d", "d_roi_30d", "d_roi_90d", "d_cnt_30d", "d_acc_30d", "d_lt_roi", "d_lt_cnt", "d_roi_per_pick_30d",
    "capper_experience", "days_since_last", "days_since_first",
    "picks_same_day_before", "streak_entering", "discord_share_30d",
    "cons_cnt_7d", "cons_cnt_30d", "cons_caps_30d", "cons_roi_30d", "cons_roi_per_pick_30d",
    "implied_prob", "log_odds", "is_dog",
    "msg_len", "msg_words", "has_lock", "has_star", "has_free", "has_half",
    "has_parlay", "has_rating", "has_units", "rating_num", "units_num",
    "emoji_count", "excl_count", "has_american_odds",
    "weekday", "month", "is_parlay", "is_discord",
]
CATEGORICAL_FEATURES = ["league_name", "sport", "bet_type_name", "odds_bucket"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def prepare(df):
    df = df.copy()
    df = df[df["outcome"].isin([1.0, 0.0])].copy()
    df = df.sort_values("pick_date").reset_index(drop=True)
    for c in CATEGORICAL_FEATURES:
        df[c] = df[c].astype("category")
    return df


def to_dmatrix(d):
    return xgb.DMatrix(d[FEATURES], label=d["outcome"], enable_categorical=True)


def fit_model(train, val):
    params = dict(
        objective="binary:logistic",
        eval_metric="logloss",
        eta=0.03,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=3,
        reg_lambda=2.0,
        reg_alpha=1.0,
        tree_method="hist",
        enable_categorical=True,
        n_jobs=-1,
        seed=42,
    )
    dtrain = to_dmatrix(train)
    dval = to_dmatrix(val)
    model = xgb.train(
        params, dtrain, num_boost_round=2000,
        evals=[(dtrain, "train"), (dval, "val")],
        early_stopping_rounds=80, verbose_eval=False,
    )
    return model


def select(probs, d, min_prob=0.55, min_edge=0.03, min_odds=1.7, max_odds=2.6,
           max_bets_per_day=4, min_capper_cnt_30d=5, discord_only=True):
    """Apply selection filters, daily cap by top prob. Returns filtered df."""
    s = d.copy()
    s["prob"] = probs
    s["edge"] = s["prob"] - s["implied_prob"]
    m = (s["prob"] >= min_prob) & (s["edge"] >= min_edge) & \
        (s["dec_odds"] >= min_odds) & (s["dec_odds"] <= max_odds) & \
        (s["cnt_30d"] >= min_capper_cnt_30d)
    if discord_only:
        m &= s["is_discord"] == 1
    s = s[m]
    if s.empty:
        return s
    s = s.sort_values(["pick_date", "prob"], ascending=[True, False])
    s["day_rank"] = s.groupby("pick_date").cumcount()
    s = s[s["day_rank"] < max_bets_per_day]
    return s


def search_thresholds(val_probs, val_df, min_n=60):
    """Grid search over selection params to maximize CappersTracked adjusted ROI.
    Coarse grid on purpose: fine grids overfit a single month.
    """
    results = []
    grid = itertools.product(
        [0.52, 0.56, 0.60, 0.64],      # min_prob
        [0.02, 0.05],                  # min_edge
        [2, 4],                        # max_bets_per_day
        [0, 5, 10],                    # min_capper_cnt_30d
        [True],                        # discord_only (emphasis)
    )
    for min_prob, min_edge, mbd, mcc, d_only in grid:
        sel = select(val_probs, val_df, min_prob=min_prob, min_edge=min_edge,
                     max_bets_per_day=mbd, min_capper_cnt_30d=mcc, discord_only=d_only)
        if len(sel) < min_n:
            continue
        sc = grade_picks(sel)
        results.append({
            "min_prob": round(float(min_prob), 2), "min_edge": min_edge,
            "max_bets_per_day": mbd, "min_capper_cnt_30d": mcc,
            **{k: sc[k] for k in ["n", "wr", "profit", "roi", "adj_roi", "grade"]},
        })
    if not results:
        return None, pd.DataFrame()
    rdf = pd.DataFrame(results)
    # Maximize adjusted ROI; tie-break on volume (more profit at same grade)
    rdf = rdf.sort_values(["adj_roi", "n"], ascending=[False, False])
    best = rdf.iloc[0].to_dict()
    return best, rdf


def report_selection(name, df):
    sc = grade_picks(df)
    if sc["n"] == 0:
        print(f"  {name}: no selections")
        return
    days = (df["pick_date"].max() - df["pick_date"].min()).days + 1 if len(df) else 0
    print(f"  {name}: n={sc['n']} record={sc['wins']}-{sc['losses']} "
          f"WR={sc['wr']*100 if sc['wr'] is not None else float('nan'):.1f}% "
          f"profit={sc['profit']:+.1f}u ROI={sc['roi']*100 if sc['roi'] is not None else float('nan'):.1f}% "
          f"ADJ_ROI={sc['adj_roi']*100 if sc['adj_roi'] is not None else float('nan'):.1f}% "
          f"GRADE={sc['grade']} ({sc['n']/days:.2f}/day)")


def main():
    df = load_data()
    df = build_features(df)
    df = prepare(df)
    print(f"Graded picks: {len(df)} | {df['pick_date'].min().date()} -> {df['pick_date'].max().date()}")

    train = df[df["pick_date"] <= TRAIN_END]
    val1 = df[(df["pick_date"] > TRAIN_END) & (df["pick_date"] <= VAL1_END)]  # tune
    val2 = df[(df["pick_date"] > VAL1_END) & (df["pick_date"] <= VAL2_END)]   # select by generalization
    val = pd.concat([val1, val2])
    test = df[df["pick_date"] > VAL2_END]
    print(f"Train: {len(train)} | Tune: {len(val1)} | Select: {len(val2)} | Test: {len(test)}")

    # ---------- Baselines on validation ----------
    print("\n=== VALIDATION BASELINES ===")
    report_selection("All val picks", val)
    report_selection("Discord val picks", val[val["is_discord"] == 1])

    # ---------- Train two variants ----------
    print("\n=== TRAINING ===")
    model_all = fit_model(train, val)
    print(f"Model A (all picks): best_iter={model_all.best_iteration}")
    train_d = train[train["is_discord"] == 1]
    model_disc = fit_model(train_d, val)
    print(f"Model B (discord only): best_iter={model_disc.best_iteration}")

    val1_probs_a = model_all.predict(to_dmatrix(val1))
    val1_probs_b = model_disc.predict(to_dmatrix(val1))
    val2_probs_a = model_all.predict(to_dmatrix(val2))
    val2_probs_b = model_disc.predict(to_dmatrix(val2))

    # Nested tuning: enumerate configs on val1 (Apr-May), rank by val2 (June).
    print("\n=== NESTED TUNING (tune Apr-May, select by June) ===")
    _, grid_a = search_thresholds(val1_probs_a, val1, min_n=30)
    _, grid_b = search_thresholds(val1_probs_b, val1, min_n=30)
    for name, grid, vp2, v2 in [("A", grid_a, val2_probs_a, val2), ("B", grid_b, val2_probs_b, val2)]:
        if grid.empty:
            print(f"Model {name}: no config survived")
            continue
        cols = ["min_prob", "min_edge", "max_bets_per_day", "min_capper_cnt_30d"]
        grid["jun_adj_roi"] = [grade_picks(select(vp2, v2, **{k: r[k] for k in cols},
                                                   discord_only=True))["adj_roi"] or 0 for _, r in grid.iterrows()]
        grid["jun_n"] = [grade_picks(select(vp2, v2, **{k: r[k] for k in cols},
                                              discord_only=True))["n"] for _, r in grid.iterrows()]
        grid = grid.sort_values(["jun_adj_roi", "jun_n"], ascending=[False, False])
        top = grid.iloc[0]
        print(f"Model {name} top config (Apr-May adj {top['adj_roi']:.2%} -> June adj {top['jun_adj_roi']:.2%}, "
              f"n={top['jun_n']}): min_prob={top['min_prob']} min_edge={top['min_edge']} "
              f"mbd={top['max_bets_per_day']} mcc={top['min_capper_cnt_30d']}")

    best_a = None if grid_a.empty else grid_a.iloc[0]
    best_b = None if grid_b.empty else grid_b.iloc[0]
    if best_a is None:
        champion, model, best = "B", model_disc, best_b
    elif best_b is None:
        champion, model, best = "A", model_all, best_a
    else:
        champion = "A" if best_a["jun_adj_roi"] >= best_b["jun_adj_roi"] else "B"
        model = model_all if champion == "A" else model_disc
        best = best_a if champion == "A" else best_b
    print(f"Champion: Model {champion} (June adj ROI {best['jun_adj_roi']:.2%})")

    cfg = {k: best[k] for k in ["min_prob", "min_edge", "max_bets_per_day", "min_capper_cnt_30d"]}

    # ---------- Frozen evaluation on test ----------
    print("\n=== TEST (frozen config) ===")
    test_probs = model.predict(to_dmatrix(test))
    test_sel = select(test_probs, test, **cfg, discord_only=True)
    report_selection("Test: Discord picks only", test_sel)
    test_sel_all = select(test_probs, test, **cfg, discord_only=False)
    report_selection("Test: all picks", test_sel_all)

    # Feature importance
    imp = sorted(zip(FEATURES, model.get_score(importance_type="gain").values()),
                 key=lambda x: -x[1]) if model.get_score(importance_type="gain") else []
    print("\n=== TOP FEATURES ===")
    for f, g in imp[:20]:
        print(f"  {f}: {g:.0f}")

    # Save artifacts
    os.makedirs(os.path.join(BASE, "models"), exist_ok=True)
    model.save_model(os.path.join(BASE, "models", "ruby_champion.json"))
    with open(os.path.join(BASE, "models", "ruby_config.json"), "w") as fh:
        json.dump({"features": FEATURES, "champion": champion,
                   "train_end": TRAIN_END, "val1_end": VAL1_END, "val2_end": VAL2_END, **cfg,
                   "jun_adj_roi": float(best["jun_adj_roi"]), "test_adj_roi": float(grade_picks(test_sel)["adj_roi"]),
                   "test_grade": grade_picks(test_sel)["grade"]}, fh, indent=2, default=str)
    print("\nSaved: models/ruby_champion.json + ruby_config.json")

    # Write report
    lines = [
        "# v7 RUBY - Discord-First Score-Maximizing Sniper\n",
        f"Data: {len(df)} graded picks, {df['pick_date'].min().date()} -> {df['pick_date'].max().date()}",
        f"Split: train <= {TRAIN_END} | tune {TRAIN_END}..{VAL1_END} | select {VAL1_END}..{VAL2_END} | test > {VAL2_END}\n",
        "## Validation baselines",
        f"- All val picks: {grade_picks(val)['grade']} (adj ROI {grade_picks(val)['adj_roi']:.2%})",
        f"- Discord val picks: {grade_picks(val[val['is_discord']==1])['grade']} (adj ROI {grade_picks(val[val['is_discord']==1])['adj_roi']:.2%})",
        f"- Tuned Model {champion} by June adj ROI {best['jun_adj_roi']:.2%}\n",
        "## Test (frozen)",
        f"- Discord picks: {grade_picks(test_sel)['grade']} (adj ROI {grade_picks(test_sel)['adj_roi']:.2%}, "
        f"n={grade_picks(test_sel)['n']}, WR={grade_picks(test_sel)['wr']:.1%}, profit={grade_picks(test_sel)['profit']:+.1f}u)",
    ]
    with open(os.path.join(BASE, "REPORT.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"Report: {os.path.join(BASE, 'REPORT.md')}")


if __name__ == "__main__":
    main()
