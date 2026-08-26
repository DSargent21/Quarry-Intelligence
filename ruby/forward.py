"""v7 RUBY - Forward Test Tracker.

Recomputes selections from the live database each run using the FROZEN models +
policy (deployed 2026-08-26), grades them as results arrive, and publishes the
ledger to docs/ruby_forward.json + injects it into docs/web/ruby.html.

The policy and models are frozen: nothing here is retrained or re-tuned. This is
the September-onward forward confirmation of the Jun-Aug walk-forward edge.

Usage:
  python3 ruby/forward.py                 # normal run (start = stored or today)
  python3 ruby/forward.py --start 2026-08-10   # override start for testing
  python3 ruby/forward.py --reset-start   # force start = today
"""
import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
import xgboost as xgb
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DOCS = os.path.join(ROOT, "docs")
DATA_JSON = os.path.join(DOCS, "ruby_forward.json")
PAGE = os.path.join(DOCS, "web", "ruby.html")

# local dev: workspace .env sits one level above the Quarry repo
load_dotenv(os.path.join(os.path.dirname(ROOT), ".env"))
load_dotenv(os.path.join(ROOT, ".env"))
os.environ.setdefault("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY", ""))

sys.path.insert(0, BASE)
from fetch import load_data
from features import build_features
from run import FEATURES

POLICY = {
    "min_prob": 0.56, "min_edge": 0.01, "max_bets_per_day": 6,
    "min_capper_cnt_30d": 3, "min_odds": 1.85, "max_odds": 2.2,
    "discord_only": True,
}

VERIFICATION = {
    "label": "Frozen verification (Jun-Aug 2026, pre-deployment)",
    "n": 307, "roi": 0.110, "tstat": 2.04, "months_pos": "3/3",
    "profit": 33.8,
    "baselines": {"all_discord_roi": -0.031, "top_prob_roi": -0.030},
    "caveat": "Borderline significant (p~0.04). Top capper ~50% of profit. "
              "Graded vs posted odds, not closing lines.",
}

CATEGORICAL = ["league_name", "sport", "bet_type_name", "odds_bucket"]


def prepare_all(df):
    df = df.copy()
    df = df.sort_values("pick_date").reset_index(drop=True)
    for c in CATEGORICAL:
        df[c] = df[c].astype("category")
    return df


def to_dm(d):
    return xgb.DMatrix(d[FEATURES], enable_categorical=True)


def load_models():
    ma = xgb.Booster()
    mb = xgb.Booster()
    ma.load_model(os.path.join(BASE, "models", "ruby_all.json"))
    mb.load_model(os.path.join(BASE, "models", "ruby_discord.json"))
    return ma, mb


def select(d):
    s = d.copy()
    s["edge"] = s["prob"] - s["implied_prob"]
    m = ((s["prob"] >= POLICY["min_prob"]) & (s["edge"] >= POLICY["min_edge"])
         & (s["dec_odds"] >= POLICY["min_odds"]) & (s["dec_odds"] <= POLICY["max_odds"])
         & (s["cnt_30d"] >= POLICY["min_capper_cnt_30d"]))
    if POLICY["discord_only"]:
        m &= s["is_discord"] == 1
    s = s[m]
    if s.empty:
        return s
    s = s.sort_values(["pick_date", "prob"], ascending=[True, False])
    s["day_rank"] = s.groupby("pick_date").cumcount()
    return s[s["day_rank"] < POLICY["max_bets_per_day"]]


def status_of(row):
    r = str(row.get("result", "")).lower().strip()
    if row["outcome"] == 1.0:
        return "WIN"
    if row["outcome"] == 0.0:
        return "LOSS"
    if r in ("push", "void", "refund"):
        return "PUSH"
    return "PENDING"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=None)
    ap.add_argument("--reset-start", action="store_true")
    args = ap.parse_args()

    # resolve forward-test start date (persisted once)
    meta_prev = {}
    if os.path.exists(DATA_JSON):
        try:
            meta_prev = json.load(open(DATA_JSON)).get("meta", {})
        except Exception:
            meta_prev = {}
    if args.start:
        start = args.start
    elif args.reset_start or not meta_prev.get("start_date"):
        # forward test begins the day after deployment: picks are only counted
        # from tomorrow onward so the ledger starts clean at 0.
        start = (pd.Timestamp.now() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        start = meta_prev["start_date"]

    print(f"Fetching + building features...")
    data = load_data()
    df = build_features(data)
    df = prepare_all(df)
    print(f"Rows: {len(df)} | {df['pick_date'].min().date()} -> {df['pick_date'].max().date()}")

    ma, mb = load_models()
    future = df[df["pick_date"] >= start].copy()
    if future.empty:
        print("No picks since start date; ledger will be empty.")
        future["prob"] = np.nan
    else:
        dm = to_dm(future)
        future["prob"] = 0.5 * (ma.predict(dm) + mb.predict(dm))

    sel = select(future)

    # ledger
    rows = []
    for _, r in sel.iterrows():
        st = status_of(r)
        profit = None if st not in ("WIN", "LOSS") else float(r["profit_1u"])
        rows.append({
            "id": str(r["id"]),
            "date": str(r["pick_date"].date()),
            "capper": str(r.get("capper_name") or "unknown"),
            "league": str(r.get("league_name") or "Other"),
            "selection": str(r.get("pick_norm") or r.get("pick_value") or ""),
            "odds": None if pd.isna(r["odds_american"]) else float(r["odds_american"]),
            "dec": float(r["dec_odds"]),
            "prob": round(float(r["prob"]), 4) if not pd.isna(r["prob"]) else None,
            "edge": round(float(r["prob"]) - float(r["implied_prob"]), 4) if not pd.isna(r["prob"]) else None,
            "status": st,
            "profit": round(profit, 2) if profit is not None else None,
        })
    rows.sort(key=lambda x: x["date"], reverse=True)

    # stats on graded selections
    g = sel[sel["outcome"].isin([1.0, 0.0])]
    n = len(g)
    wins = int((g["outcome"] == 1).sum())
    losses = n - wins
    net = float(g["profit_1u"].sum()) if n else 0.0
    roi = float(g["profit_1u"].mean()) if n else None
    wr = wins / n if n else None
    tstat = (float(g["profit_1u"].mean()) / (float(g["profit_1u"].std()) / np.sqrt(n))) if n > 1 else None
    pending = int((sel["outcome"].isna()).sum())
    days_live = (pd.Timestamp.now() - pd.Timestamp(start)).days + 1
    by_month = []
    if n:
        g2 = g.assign(mm=g["pick_date"].dt.to_period("M"))
        for mm, gg in g2.groupby("mm"):
            by_month.append({
                "month": str(mm), "n": int(len(gg)),
                "wr": round(float(gg["outcome"].mean()), 4),
                "roi": round(float(gg["profit_1u"].mean()), 4),
                "net": round(float(gg["profit_1u"].sum()), 2),
            })

    # baselines since start (graded discord)
    gd = df[(df["pick_date"] >= start) & df["outcome"].isin([1.0, 0.0]) & (df["is_discord"] == 1)]
    bl_all = float(gd["profit_1u"].mean()) if len(gd) else None
    if len(gd):
        gd2 = gd.copy()
        gd2["prob"] = 0.5 * (ma.predict(to_dm(gd2)) + mb.predict(to_dm(gd2)))
        gd2 = gd2.sort_values(["pick_date", "prob"], ascending=[True, False])
        gd2["rk"] = gd2.groupby("pick_date").cumcount()
        gd2 = gd2[gd2["rk"] < 50]
        bl_top = float(gd2["profit_1u"].mean())
    else:
        bl_top = None

    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    todays = [r for r in rows if r["date"] == today]

    payload = {
        "meta": {
            "last_update": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M UTC"),
            "start_date": start,
            "days_live": days_live,
            "status": "OPERATIONAL",
            "policy": POLICY,
            "verification": VERIFICATION,
        },
        "stats": {
            "n": n, "wins": wins, "losses": losses, "pending": pending,
            "wr": round(wr, 4) if wr is not None else None,
            "roi": round(roi, 4) if roi is not None else None,
            "net": round(net, 2), "tstat": round(tstat, 2) if tstat is not None else None,
        },
        "baselines": {"all_discord_roi": round(bl_all, 4) if bl_all is not None else None,
                      "top_prob_roi": round(bl_top, 4) if bl_top is not None else None},
        "today": todays,
        "by_month": by_month,
        "ledger": rows,
    }

    os.makedirs(DOCS, exist_ok=True)
    with open(DATA_JSON, "w") as fh:
        json.dump(payload, fh, indent=2)
    print(f"Wrote {DATA_JSON}: n={n} net={net:+.2f}u roi={roi if roi is None else round(roi,4)} tstat={tstat}")

    # inject into page
    if os.path.exists(PAGE):
        html = open(PAGE).read()
        block = f"<script>const RUBY_FORWARD = {json.dumps(payload, indent=2)};</script>"
        marker_s, marker_e = "<!-- RUBY_DATA_START -->", "<!-- RUBY_DATA_END -->"
        if marker_s in html and marker_e in html:
            head, tail = html.split(marker_s, 1)
            _, tail = tail.split(marker_e, 1)
            html = head + marker_s + "\n" + block + "\n" + marker_e + tail
            with open(PAGE, "w") as fh:
                fh.write(html)
            print(f"Injected data into {PAGE}")
        else:
            print(f"WARNING: markers not found in {PAGE}; page not updated.")
    else:
        print(f"WARNING: {PAGE} missing; page not updated.")

    # machine-readable summary for the workflow
    print(json.dumps({"n": n, "net": round(net, 2), "roi": round(roi, 4) if roi is not None else None,
                      "tstat": round(tstat, 2) if tstat is not None else None, "pending": pending}))


if __name__ == "__main__":
    main()
