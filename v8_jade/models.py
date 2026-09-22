"""v8 JADE - model layer.

Discord-only XGBoost blend (all-picks + Discord-specialist), trained with
CAUSAL early stopping: for a fold whose evaluation window starts at T,
the early-stopping set is strictly before T (last 45 days of training),
never the evaluation window itself. Probabilities are isotonically
recalibrated per fold.
"""
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.isotonic import IsotonicRegression

SEED = 7

NUMERIC_FEATURES = [
    "acc_7d", "acc_14d", "acc_30d", "acc_60d", "acc_90d",
    "roi_7d", "roi_14d", "roi_30d", "roi_60d", "roi_90d",
    "vol_30d", "vol_90d", "cnt_7d", "cnt_30d", "cnt_90d",
    "roi_vol_ratio_30d", "sharpe_30d", "acc_mom_7_30", "acc_mom_14_60", "roi_per_pick_30d",
    "lt_cnt", "lt_roi", "lt_acc",
    "d_roi_7d", "d_roi_30d", "d_roi_90d", "d_cnt_30d", "d_acc_30d", "d_lt_roi", "d_lt_cnt",
    "d_roi_per_pick_30d",
    "capper_experience", "days_since_last", "days_since_first",
    "picks_same_day_before", "streak_entering", "discord_share_30d",
    "cons_cnt_7d", "cons_cnt_30d", "cons_caps_30d", "cons_roi_30d", "cons_roi_per_pick_30d",
    "implied_prob", "log_odds", "is_dog",
    "msg_len", "msg_words", "has_lock", "has_star", "has_free", "has_half",
    "has_parlay", "has_rating", "has_units", "rating_num", "units_num",
    "emoji_count", "excl_count", "has_american_odds",
    "weekday", "month", "is_parlay", "is_discord",
    # Jade additions
    "band_cnt_30d", "band_cnt_90d", "band_roi_30d", "band_roi_90d",
    "band_roi_lt", "band_wr_lt", "shrunk_acc_30d", "shrunk_acc_lt",
    "capper_roi_30d_j", "ev_implied",
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


def to_dm(d):
    return xgb.DMatrix(d[FEATURES], enable_categorical=True)


def _params():
    return dict(
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
        seed=SEED,
    )


def fit_pair(train, es):
    """Fit the (all-picks, discord-only) pair.

    es: early-stopping set - strictly BEFORE the fold's evaluation window.
    """
    train_d = train[train["is_discord"] == 1]
    dtr, des = to_dmatrix(train), to_dmatrix(es)
    ma = xgb.train(_params(), dtr, num_boost_round=1200,
                   evals=[(dtr, "train"), (des, "es")],
                   early_stopping_rounds=60, verbose_eval=False)
    dtr_d = to_dmatrix(train_d)
    mb = xgb.train(_params(), dtr_d, num_boost_round=1200,
                   evals=[(dtr_d, "train"), (des, "es")],
                   early_stopping_rounds=60, verbose_eval=False)
    return ma, mb


def predict_avg(models, d, iso=None):
    """Average predictions of the given boosters; optional isotonic recalibration."""
    dm = to_dm(d)
    ps = [m.predict(dm) for m in models]
    p = np.mean(ps, axis=0)
    if iso is not None:
        p = np.clip(iso.predict(p), 1e-6, 1 - 1e-6)
    return p


def fit_isotonic(p, y):
    iso = IsotonicRegression(y_min=0.02, y_max=0.95, out_of_bounds="clip")
    iso.fit(p, y)
    return iso
