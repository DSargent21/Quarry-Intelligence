"""v7 RUBY - feature engineering.

Every feature is strictly point-in-time (known before the pick was posted):
- Capper rolling stats use daily aggregates shifted +1 day (known_date), merged
  back with merge_asof(direction='backward').
- Consensus counts picks from PREVIOUS days only (same known_date shift).
- No rolling window includes the current pick's own result or same-day results.
"""
import numpy as np
import pandas as pd
import re

WINDOWS = [7, 14, 30, 60, 90]

TEAM_ABBREVS = {
    "gsw": "golden state warriors", "gs": "golden state warriors", "lal": "los angeles lakers",
    "phi": "philadelphia", "phx": "phoenix", "bos": "boston", "dal": "dallas", "chi": "chicago",
    "nyk": "new york knicks", "okc": "oklahoma city thunder", "mia": "miami", "den": "denver",
    "mil": "milwaukee", "tor": "toronto", "lac": "la clippers", "sas": "san antonio",
    "min": "minnesota", "utah": "utah", "por": "portland", "sac": "sacramento", "mem": "memphis",
    "hou": "houston", "det": "detroit", "cha": "charlotte", "orl": "orlando", "was": "washington",
    "atl": "atlanta", "cle": "cleveland", "ind": "indiana", "bkn": "brooklyn",
}


def normalize_pick(s):
    if not isinstance(s, str):
        return ""
    s = s.lower().strip()
    s = re.sub(r"(\d)\.0(?=\s|$)", r"\1", s)
    s = re.sub(r"[,;:!?'\"()]", "", s)
    s = re.sub(r"([+-])\s+", r"\1", s)
    s = re.sub(r"\b(pk|pick|even)\b", "0", s)
    words = s.split()
    s = " ".join([TEAM_ABBREVS.get(w, w) for w in words])
    return re.sub(r"\s+", " ", s).strip()


def streak_entering(outcomes):
    """Length of same-outcome run immediately before each pick (0 if unknown)."""
    vals = outcomes.to_numpy(dtype=np.float64)
    n = len(vals)
    res = np.zeros(n, dtype=np.float64)
    prev = None
    run = 0
    for i in range(n):
        res[i] = run if prev is not None else 0.0
        o = vals[i]
        if np.isnan(o):
            prev, run = None, 0
        elif prev is None or o == prev:
            prev = o
            run = run + 1
        else:
            prev = o
            run = 1
    return res


def add_text_features(df):
    msg = df["message"].fillna("")
    df["msg_len"] = msg.str.len().fillna(0)
    df["msg_words"] = msg.str.split().str.len().fillna(0)
    df["has_lock"] = msg.str.contains(r"\block\b|best bet|top play|max bet|lock of|sure thing", case=False, regex=True).astype(int)
    df["has_star"] = msg.str.contains(r"[★⭐]", regex=True).astype(int)
    df["has_free"] = msg.str.contains(r"\bfree\b", case=False, regex=True).astype(int)
    df["has_half"] = msg.str.contains(r"\b1h\b|\b2h\b|first half|2nd half", case=False, regex=True).astype(int)
    df["has_parlay"] = msg.str.contains(r"parlay|multi", case=False, regex=True).astype(int)
    df["has_rating"] = msg.str.contains(r"rating", case=False, regex=True).astype(int)
    df["has_units"] = msg.str.contains(r"(?:\d+(?:\.\d+)?)\s*(?:u|units?|stars?)\b", case=False, regex=True).astype(int)
    df["rating_num"] = msg.str.extract(r"rating:?\s*(\d+(?:\.\d+)?)", flags=re.I)[0].astype(float).fillna(0)
    df["units_num"] = msg.str.extract(r"(\d+(?:\.\d+)?)\s*(?:u|units?)\b", flags=re.I)[0].astype(float).fillna(0)
    df["emoji_count"] = msg.str.count(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF★⭐]").fillna(0)
    df["excl_count"] = msg.str.count("!").fillna(0)
    df["has_american_odds"] = msg.str.contains(r"[-+]\d{3,4}", regex=True).astype(int)
    return df


def build_features(df):
    df = df.sort_values(["capper_id", "pick_date"]).reset_index(drop=True)
    df["pick_norm"] = df["pick_value"].apply(normalize_pick)
    df = add_text_features(df)

    # ---------- 1. Capper daily aggregates (all picks) ----------
    daily = df.groupby(["capper_id", "pick_date"], as_index=False).agg(
        wins=("outcome", "sum"),
        cnt=("outcome", "count"),
        profit=("profit_1u", "sum"),
        odds=("dec_odds", "mean"),
    )
    daily["known_date"] = daily["pick_date"] + pd.Timedelta(days=1)

    # ---------- 2. Capper daily aggregates (Discord picks only) ----------
    disc_daily = df[df["is_discord"] == 1].groupby(["capper_id", "pick_date"], as_index=False).agg(
        d_wins=("outcome", "sum"),
        d_cnt=("outcome", "count"),
        d_profit=("profit_1u", "sum"),
    )
    disc_daily["known_date"] = disc_daily["pick_date"] + pd.Timedelta(days=1)

    # ---------- 3. Rolling stats on known_date ----------
    daily = daily.sort_values(["capper_id", "known_date"])
    g = daily.groupby("capper_id")
    for w in WINDOWS:
        daily[f"acc_{w}d"] = g["wins"].transform(lambda x: x.rolling(w, min_periods=1).sum()) / \
                             (g["cnt"].transform(lambda x: x.rolling(w, min_periods=1).sum()) + 1e-9)
        daily[f"roi_{w}d"] = g["profit"].transform(lambda x: x.rolling(w, min_periods=1).sum())
        daily[f"vol_{w}d"] = g["profit"].transform(lambda x: x.rolling(w, min_periods=1).std()).fillna(0)
        daily[f"cnt_{w}d"] = g["cnt"].transform(lambda x: x.rolling(w, min_periods=1).sum())
    daily["roi_vol_ratio_30d"] = daily["roi_30d"] / (daily["vol_30d"] + 0.1)
    daily["sharpe_30d"] = daily["roi_30d"] / (daily["vol_30d"] + 0.1)
    # momentum: recent form minus baseline form (positive = improving)
    daily["acc_mom_7_30"] = daily["acc_7d"] - daily["acc_30d"]
    daily["acc_mom_14_60"] = daily["acc_14d"] - daily["acc_60d"]
    # roi per graded pick (normalizes volume vs profit)
    daily["roi_per_pick_30d"] = daily["roi_30d"] / (daily["cnt_30d"] + 1e-9)
    # lifetime stats (all history strictly before known_date)
    daily["lt_cnt"] = g["cnt"].cumsum()
    daily["lt_roi"] = g["profit"].cumsum()
    daily["lt_acc"] = g["wins"].cumsum() / (g["cnt"].cumsum() + 1e-9)

    disc_daily = disc_daily.sort_values(["capper_id", "known_date"])
    gd = disc_daily.groupby("capper_id")
    for w in [7, 30, 90]:
        disc_daily[f"d_roi_{w}d"] = gd["d_profit"].transform(lambda x: x.rolling(w, min_periods=1).sum())
        disc_daily[f"d_cnt_{w}d"] = gd["d_cnt"].transform(lambda x: x.rolling(w, min_periods=1).sum())
        disc_daily[f"d_acc_{w}d"] = gd["d_wins"].transform(lambda x: x.rolling(w, min_periods=1).sum()) / \
                                    (gd["d_cnt"].transform(lambda x: x.rolling(w, min_periods=1).sum()) + 1e-9)
    disc_daily["d_lt_roi"] = gd["d_profit"].cumsum()
    disc_daily["d_lt_cnt"] = gd["d_cnt"].cumsum()
    disc_daily["d_roi_per_pick_30d"] = disc_daily["d_roi_30d"] / (disc_daily["d_cnt_30d"] + 1e-9)

    # ---------- 4. Merge rolling features back onto picks ----------
    feat_cols = [f"{m}_{w}d" for w in WINDOWS for m in ["acc", "roi", "vol", "cnt"]] + \
                ["roi_vol_ratio_30d", "sharpe_30d", "lt_cnt", "lt_roi", "lt_acc",
                 "acc_mom_7_30", "acc_mom_14_60", "roi_per_pick_30d"]
    daily_f = daily[["capper_id", "known_date"] + feat_cols].rename(columns={"known_date": "feat_date"})
    df = pd.merge_asof(df.sort_values("pick_date"), daily_f.sort_values("feat_date"),
                       left_on="pick_date", right_on="feat_date", by="capper_id", direction="backward")

    dcols = [f"d_{m}_{w}d" for w in [7, 30, 90] for m in ["roi", "cnt", "acc"]] + \
            ["d_lt_roi", "d_lt_cnt", "d_roi_per_pick_30d"]
    disc_f = disc_daily[["capper_id", "known_date"] + dcols].rename(columns={"known_date": "feat_date"})
    df = pd.merge_asof(df.sort_values("pick_date"), disc_f.sort_values("feat_date"),
                       left_on="pick_date", right_on="feat_date", by="capper_id", direction="backward")

    # ---------- 5. Capper identity / cadence (point-in-time) ----------
    df["capper_experience"] = df.groupby("capper_id").cumcount()  # rows before current
    df["days_since_last"] = df.groupby("capper_id")["pick_date"].diff().dt.days.fillna(999)
    first_dates = df.groupby("capper_id")["pick_date"].transform("min")
    df["days_since_first"] = (df["pick_date"] - first_dates).dt.days
    df["picks_same_day_before"] = df.groupby(["capper_id", "pick_date"]).cumcount()
    df["streak_entering"] = df.groupby("capper_id")["outcome"].transform(streak_entering)
    df["discord_share_30d"] = df["d_cnt_30d"] / (df["cnt_30d"] + 1e-9)

    # ---------- 6. Consensus (previous days only, per league x pick) ----------
    df["cons_key"] = df["league_name"].fillna("Other") + "|" + df["pick_norm"]
    cons = df.groupby(["cons_key", "pick_date"], as_index=False).agg(
        n_picks=("capper_id", "count"),
        n_cappers=("capper_id", "nunique"),
        roi_sum=("roi_30d", "sum"),
    )
    cons["known_date"] = cons["pick_date"] + pd.Timedelta(days=1)
    cons = cons.sort_values(["cons_key", "known_date"])
    gc = cons.groupby("cons_key")
    for w in [7, 30]:
        cons[f"cons_cnt_{w}d"] = gc["n_picks"].transform(lambda x: x.rolling(w, min_periods=1).sum())
        cons[f"cons_caps_{w}d"] = gc["n_cappers"].transform(lambda x: x.rolling(w, min_periods=1).sum())
        cons[f"cons_roi_{w}d"] = gc["roi_sum"].transform(lambda x: x.rolling(w, min_periods=1).sum())
    cons["cons_roi_per_pick_30d"] = cons["cons_roi_30d"] / (cons["cons_cnt_30d"] + 1e-9)
    cons_f = cons[["cons_key", "known_date", "cons_cnt_7d", "cons_cnt_30d", "cons_caps_7d", "cons_caps_30d",
                   "cons_roi_7d", "cons_roi_30d", "cons_roi_per_pick_30d"]].rename(columns={"known_date": "feat_date"})
    df = pd.merge_asof(df.sort_values("pick_date"), cons_f.sort_values("feat_date"),
                       left_on="pick_date", right_on="feat_date", by="cons_key", direction="backward")

    # ---------- 7. Market / context features ----------
    df["implied_prob"] = 1 / df["dec_odds"]
    df["log_odds"] = np.log(df["dec_odds"])
    df["is_dog"] = (df["dec_odds"] >= 2.0).astype(int)
    df["odds_bucket"] = pd.cut(
        df["odds_american"].fillna(-110),
        bins=[-np.inf, -200, -101, 100, 200, np.inf],
        labels=["heavy_fav", "fav", "near_even", "dog", "heavy_dog"],
    )
    df["weekday"] = df["pick_date"].dt.weekday
    df["month"] = df["pick_date"].dt.month
    df["is_parlay"] = df["is_parlay"].fillna(False).astype(int)

    df["sport"] = df["sport"].fillna("Other")
    df["league_name"] = df["league_name"].fillna("Other")
    df["bet_type_name"] = df["bet_type_name"].fillna("Unknown")

    # ---------- 8. Fill ----------
    # NEVER touch outcome / profit / odds: pushes and ungraded picks have NaN
    # outcome and must stay NaN (excluded from grading), not become fake losses.
    protected = {"outcome", "profit_1u", "dec_odds", "odds_american", "unit"}
    num_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c not in protected]
    df[num_cols] = df[num_cols].fillna(0)
    df["pick_norm"] = df["pick_norm"].fillna("")
    return df
