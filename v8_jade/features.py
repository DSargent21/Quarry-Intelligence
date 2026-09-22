"""v8 JADE - features.

Reuses v7 RUBY's proven point-in-time feature builder (daily aggregates shifted
+1 day via known_date, merge_asof backward, consensus from previous days only -
no rolling window ever includes the current pick's own result or same-day
results) and adds two Jade feature families:

  A. Capper odds-band ROI history: the capper's own past ROI specifically in the
     value band [1.80, 2.40] decimal, where self-selection edge lives. Built
     from band-day aggregates shifted +1 day (causal, same pattern as v7).
  B. Grading-mirrored shrunk skill: capper win rate shrunk with k=24 toward 0.5
     (same shrinkage math as the target grade, at 30d and lifetime horizons).
"""
import os
import importlib.util
import numpy as np
import pandas as pd

# Load v7 RUBY's proven feature builder by explicit path (a plain
# "import features" would resolve to this very module - same name).
#
# The vendored copy inside this package is authoritative: the daily GitHub
# Actions job only syncs v8_jade/, so reaching for a sibling directory outside
# the package (as an earlier version did) breaks every scheduled run. The
# workspace/repo paths remain as fallbacks for local experimentation.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_V7_CANDIDATES = [
    os.path.join(_BASE_DIR, "_v7_features.py"),                          # vendored (authoritative)
    os.path.join(os.path.dirname(_BASE_DIR), "v7_ruby", "features.py"),  # dev workspace
    os.path.join(os.path.dirname(_BASE_DIR), "ruby", "features.py"),     # repo sibling
]
_V7_PATH = next((p for p in _V7_CANDIDATES if os.path.exists(p)), None)
if _V7_PATH is None:
    raise FileNotFoundError(
        "v7 feature builder not found. Looked in:\n  " + "\n  ".join(_V7_CANDIDATES))

# Dev-time drift guard: if a non-vendored copy exists and differs, the vendored
# one still wins, but silent divergence would invalidate comparisons - so say so.
if _V7_PATH != _V7_CANDIDATES[0]:
    try:
        import hashlib
        _h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
        if os.path.exists(_V7_CANDIDATES[0]) and _h(_V7_PATH) != _h(_V7_CANDIDATES[0]):
            print(f"WARNING: {_V7_PATH} differs from the vendored {_V7_CANDIDATES[0]}; "
                  "the vendored copy is authoritative - re-vendor if this was intentional.")
    except Exception:
        pass

_spec = importlib.util.spec_from_file_location("v7_features", _V7_PATH)
_v7mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_v7mod)
_v7_build_features = _v7mod.build_features

BAND_LO, BAND_HI = 1.80, 2.40

# Bump when feature semantics change; the forward ledger records which version
# scored its picks and refuses stale merges.
FEATURES_VERSION = "jade-1"

JADE_NUMERIC = [
    "band_cnt_30d", "band_cnt_90d", "band_roi_30d", "band_roi_90d",
    "band_roi_lt", "band_wr_lt", "shrunk_acc_30d", "shrunk_acc_lt",
    "capper_roi_30d_j", "ev_implied",
]


def add_jade_features(df):
    df = df.copy()

    # ---------- A. capper odds-band ROI history (causal: +1 day shift) ----------
    in_band = (df["dec_odds"] >= BAND_LO) & (df["dec_odds"] <= BAND_HI)
    band = df[in_band].groupby(["capper_id", "pick_date"], as_index=False).agg(
        b_wins=("outcome", "sum"), b_cnt=("outcome", "count"), b_profit=("profit_1u", "sum"))
    band["known_date"] = band["pick_date"] + pd.Timedelta(days=1)
    band = band.sort_values(["capper_id", "known_date"])
    gb = band.groupby("capper_id")
    for w in [30, 90]:
        band[f"band_cnt_{w}d"] = gb["b_cnt"].transform(lambda x: x.rolling(w, min_periods=1).sum())
        band[f"band_roi_{w}d"] = gb["b_profit"].transform(lambda x: x.rolling(w, min_periods=1).sum())
    band["band_roi_lt"] = gb["b_profit"].cumsum()
    band["band_wr_lt"] = gb["b_wins"].cumsum() / (gb["b_cnt"].cumsum() + 1e-9)
    band_f = band[["capper_id", "known_date", "band_cnt_30d", "band_cnt_90d",
                   "band_roi_30d", "band_roi_90d", "band_roi_lt", "band_wr_lt"]].rename(
        columns={"known_date": "feat_date_band"})
    df = pd.merge_asof(df.sort_values("pick_date"), band_f.sort_values("feat_date_band"),
                       left_on="pick_date", right_on="feat_date_band", by="capper_id",
                       direction="backward")
    df = df.drop(columns=["feat_date_band"])

    # ---------- B. grading-mirrored shrunk skill (k=24 toward 0.5) ----------
    daily = df.groupby(["capper_id", "pick_date"], as_index=False).agg(
        wins=("outcome", "sum"), cnt=("outcome", "count"), profit=("profit_1u", "sum"))
    daily["known_date"] = daily["pick_date"] + pd.Timedelta(days=1)
    daily = daily.sort_values(["capper_id", "known_date"])
    g = daily.groupby("capper_id")
    daily["w30"] = g["wins"].transform(lambda x: x.rolling(30, min_periods=1).sum())
    daily["c30"] = g["cnt"].transform(lambda x: x.rolling(30, min_periods=1).sum())
    daily["lt_w"] = g["wins"].cumsum()
    daily["lt_c"] = g["cnt"].cumsum()
    daily["shrunk_acc_30d"] = (daily["w30"] + 12.0 * 0.5) / (daily["c30"] + 24.0)
    daily["shrunk_acc_lt"] = (daily["lt_w"] + 12.0 * 0.5) / (daily["lt_c"] + 24.0)
    daily["capper_roi_30d_j"] = g["profit"].transform(
        lambda x: x.rolling(30, min_periods=1).sum()) / (daily["c30"] + 1e-9)
    daily_f = daily[["capper_id", "known_date", "shrunk_acc_30d", "shrunk_acc_lt",
                     "capper_roi_30d_j"]].rename(columns={"known_date": "feat_date_skill"})
    df = pd.merge_asof(df.sort_values("pick_date"), daily_f.sort_values("feat_date_skill"),
                       left_on="pick_date", right_on="feat_date_skill", by="capper_id",
                       direction="backward")
    df = df.drop(columns=["feat_date_skill"])

    # ---------- C. market-implied EV of a flat 1u bet at these odds ----------
    df["ev_implied"] = 2.0 * (1.0 / df["dec_odds"]) - 1.0

    # Fill: counts/ROI -> 0 (no history), shrunk rates -> neutral 0.5
    for c in ["band_cnt_30d", "band_cnt_90d", "band_roi_30d", "band_roi_90d",
              "band_roi_lt", "capper_roi_30d_j", "ev_implied"]:
        df[c] = df[c].fillna(0)
    for c in ["band_wr_lt", "shrunk_acc_30d", "shrunk_acc_lt"]:
        df[c] = df[c].fillna(0.5)
    return df


def build_features(df):
    df = _v7_build_features(df)
    df = add_jade_features(df)
    return df
