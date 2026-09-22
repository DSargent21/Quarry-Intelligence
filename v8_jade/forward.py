"""v8 JADE - daily forward tracker.

FROZEN production run: loads models + policy saved by deploy.py, fetches live
data, rebuilds point-in-time features, scores every open/today pick, applies
the frozen V6 site policy, and appends results to the ledger.

- Nothing is retrained or re-tuned here. Ever.
- Picks already in the ledger are never re-staked; results are graded as they
  land (WIN/LOSS are final - the platform's regrade pipeline can transiently
  clear a result, but the ledger never downgrades a graded pick).
- The daily cap is enforced ACROSS runs: picks registered on earlier runs own
  their date's slots; later runs only fill remaining capacity.
- Ledger records the policy + feature versions used at scoring time.

Usage (from repo root, run daily BEFORE games start):
  python3 v8_jade/forward.py                 # normal run (start = stored)
  python3 v8_jade/forward.py --reset-start   # begin ledger from tomorrow
  python3 v8_jade/forward.py --start YYYY-MM-DD
  python3 v8_jade/forward.py --dry-run       # show slate, do not touch ledger
"""
import os
import sys
import json
import argparse
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb

BASE = os.path.dirname(os.path.abspath(__file__))
LEDGER_JSON = os.path.join(BASE, "forward_ledger.json")
LEDGER_MD = os.path.join(BASE, "FORWARD_LEDGER.md")

sys.path.insert(0, BASE)
from fetch import load_data
from features import build_features, FEATURES_VERSION
from models import to_dm, CATEGORICAL_FEATURES
from score import grade_picks, grade_for

POLICY_VERSION = "v8-jade-1.1"
FINAL = {"WIN", "LOSS"}


def load_production():
    ma = xgb.Booster()
    ma.load_model(os.path.join(BASE, "models", "jade_all.json"))
    iso = pickle.load(open(os.path.join(BASE, "models", "jade_iso.pkl"), "rb"))
    meta = json.load(open(os.path.join(BASE, "models", "jade_policy.json")))
    return ma, iso, meta


def select_site(df, policy):
    """Frozen V6 site policy: band [1.80, 2.00], posted odds required,
    capper >= 5/30d, shrunk lifetime skill >= 0.55, top 5/day by calibrated
    prob (ties broken by raw model prob, deterministic)."""
    s = df[df["odds_american"].notna()]  # cannot bet without a posted price
    s = s[(s["dec_odds"] >= policy["min_odds"]) & (s["dec_odds"] <= policy["max_odds"])]
    s = s[s["cnt_30d"] >= policy["min_cnt_30d"]]
    s = s[s["shrunk_acc_lt"] >= policy["min_shrunk_acc_lt"]]
    if s.empty:
        return s
    s = s.sort_values(["pick_date", "prob", "prob_raw"], ascending=[True, False, False])
    return s.groupby("pick_date", sort=False).head(policy["max_per_day"])


def result_of(res):
    r = str(res).lower().strip()
    if r in ("win", "won"):
        return "WIN"
    if r in ("loss", "lost"):
        return "LOSS"
    if r in ("push", "void", "refund"):
        return "PUSH"
    return "PENDING"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset-start", action="store_true", help="begin ledger from tomorrow")
    ap.add_argument("--start", default=None, help="override forward-test start date (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true", help="show slate, do not touch ledger")
    args = ap.parse_args()

    ma, iso, meta = load_production()
    policy = meta["policy_site"]
    print(f"Jade forward run | policy {POLICY_VERSION} | deployed {meta['deployed']}")

    df = load_data(use_cache=False)  # always fresh for forward runs
    df = build_features(df)
    df = df.sort_values("pick_date").reset_index(drop=True)

    prev = {}
    if os.path.exists(LEDGER_JSON) and not args.reset_start:
        try:
            prev = json.load(open(LEDGER_JSON))
        except Exception:
            prev = {}
    prev_picks = {p["id"]: p for p in prev.get("picks", [])}
    if prev.get("policy_version") not in (None, POLICY_VERSION):
        print(f"NOTE: ledger started on {prev.get('policy_version')}; graded results "
              f"are preserved, new picks follow {POLICY_VERSION}.")

    start = prev.get("start_date")
    if args.start:
        start = args.start
        print(f"Forward test start overridden: {start}")
    elif args.reset_start or not start:
        start = (pd.Timestamp.now() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        print(f"Forward test starts: {start}")

    # score everything from the start date with the frozen models
    scored_mask = df["pick_date"] >= pd.Timestamp(start)
    df["prob"] = np.nan
    df["prob_raw"] = np.nan
    if scored_mask.any():
        sub = df[scored_mask].copy()
        for c in CATEGORICAL_FEATURES:
            sub[c] = sub[c].astype("category")
        raw = ma.predict(to_dm(sub))
        df.loc[scored_mask, "prob_raw"] = raw
        df.loc[scored_mask, "prob"] = np.clip(iso.predict(raw), 1e-6, 1 - 1e-6)

    slate = select_site(df[scored_mask], policy)
    print(f"Slate today: {len(slate)} candidates | "
          f"{len(slate) - sum(1 for _, r in slate.iterrows() if str(r['id']) in prev_picks)} new")

    if args.dry_run:
        cols = ["pick_date", "capper_name", "league_name", "pick_value",
                "odds_american", "prob", "shrunk_acc_lt"]
        print(slate[cols].head(12).to_string(index=False))
        return

    # id -> latest result (the source of truth for grading)
    res_map = dict(zip(df["id"].astype(str), df["result"]))

    def ledger_row(r):
        return {
            "id": str(r["id"]),
            "pick_date": str(pd.Timestamp(r["pick_date"]).date()),
            "capper": str(r.get("capper_name") or r["capper_id"]),
            "league": str(r.get("league_name") or "?"),
            "pick": str(r.get("pick_value"))[:60],
            "odds_american": None if pd.isna(r["odds_american"]) else float(r["odds_american"]),
            "prob": round(float(r["prob"]), 4),
            "shrunk_acc_lt": round(float(r["shrunk_acc_lt"]), 4),
            "added_at": str(pd.Timestamp.now()),
        }

    # ---- merge: keep every previously registered pick, never downgrade grades,
    # ---- enforce the daily cap across runs (earlier picks own their slots).
    merged = list(prev_picks.values())
    known = set(prev_picks)
    for p in merged:
        if p.get("result") in FINAL:
            continue  # graded results are final
        p["result"] = result_of(res_map.get(p["id"], "none"))

    per_date = {}
    for p in merged:
        per_date[p["pick_date"]] = per_date.get(p["pick_date"], 0) + 1

    slate_sorted = slate.sort_values(["pick_date", "prob", "prob_raw"],
                                     ascending=[True, False, False])
    for _, r in slate_sorted.iterrows():
        pid = str(r["id"])
        d = str(pd.Timestamp(r["pick_date"]).date())
        if pid in known:
            continue
        if per_date.get(d, 0) >= policy["max_per_day"]:
            continue  # date already full from earlier runs
        known.add(pid)
        per_date[d] = per_date.get(d, 0) + 1
        row = ledger_row(r)
        row["result"] = result_of(res_map.get(pid, "none"))
        merged.append(row)

    graded = [p for p in merged if p["result"] in FINAL]
    pushes = [p for p in merged if p["result"] == "PUSH"]
    pending = [p for p in merged if p["result"] == "PENDING"]
    sc = {"n": 0, "adj_roi": None, "grade": "-", "profit": 0.0, "roi": None, "wr": None}
    if graded:
        gdf = pd.DataFrame(graded)
        gdf["outcome"] = (gdf["result"] == "WIN").astype(float)
        gdf["odds_american"] = gdf["odds_american"].astype(float)
        gdf["dec_odds"] = gdf["odds_american"].apply(
            lambda o: (o / 100) + 1 if o > 0 else (100 / abs(o)) + 1 if o < 0 else 1.91)
        sc = grade_picks(gdf)

    out = {
        "policy_version": POLICY_VERSION,
        "features_version": FEATURES_VERSION,
        "start_date": start,
        "updated_at": str(pd.Timestamp.now()),
        "summary": {"graded": len(graded), "pending": len(pending), "pushes": len(pushes),
                    "profit": round(sc["profit"], 2),
                    "roi": None if sc["roi"] is None else round(sc["roi"], 4),
                    "adj_roi": None if sc["adj_roi"] is None else round(sc["adj_roi"], 4),
                    "grade": sc["grade"]},
        "picks": merged,
    }
    with open(LEDGER_JSON, "w") as fh:
        json.dump(out, fh, indent=2, default=str)

    lines = [
        "# v8 JADE - Forward Test Ledger",
        "",
        f"Start: {start} | Policy: {POLICY_VERSION} (frozen) | Updated: {out['updated_at']}",
        "",
        f"**Graded: {len(graded)} | Pending: {len(pending)} | Pushes: {len(pushes)}**",
        f"**Profit: {sc['profit']:+.1f}u | "
        f"ROI: {'-' if sc['roi'] is None else format(sc['roi'], '+.1%')} | "
        f"Adj ROI: {'-' if sc['adj_roi'] is None else format(sc['adj_roi'], '+.1%')} | "
        f"Grade: {sc['grade']}**",
        "",
        "| Date | Capper | League | Pick | Odds | Prob | Result |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in sorted(merged, key=lambda x: (x["pick_date"], x.get("capper", ""))):
        odds = "-" if p["odds_american"] is None else f"{int(p['odds_american']):+d}"
        lines.append(f"| {p['pick_date']} | {p.get('capper','?')} | {p.get('league','?')} | "
                     f"{p.get('pick','')[:40]} | {odds} | {p.get('prob',0):.3f} | {p['result']} |")
    with open(LEDGER_MD, "w") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"\nLedger: {len(graded)} graded | {len(pending)} pending | "
          f"profit {sc['profit']:+.1f}u | grade {sc['grade']}")
    print(f"Saved: {LEDGER_JSON} + {LEDGER_MD}")


if __name__ == "__main__":
    main()
