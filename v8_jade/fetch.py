"""v8 JADE - fetch layer.

Pulls all picks + supporting tables from Supabase with batching, applies the
data-quality fixes inherited from v7 RUBY (Int64 id precision, dedup, NaN outcome
protection, regraded-Discord relabeling), and caches to parquet.

Usage (from repo root):
  python3 v8_jade/fetch.py --refresh   # force live refetch
  python3 v8_jade/fetch.py             # use cache if present
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
os.environ.setdefault("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY", ""))

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "data", "picks.parquet")

PICK_COLS = ("id, pick_date, pick_value, unit, odds_american, result, capper_id, "
             "league_id, bet_type_id, source_id, source_url, is_parlay, status, "
             "created_at, raw_text")


def fetch_all(table, cols="*", batch=1000):
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    rows, start = [], 0
    while True:
        data = supabase.table(table).select(cols).range(start, start + batch - 1).execute().data
        if not data:
            break
        rows.extend(data)
        start += batch
    # dtype=object keeps bigint ids exact (avoid float64 precision loss > 2^53)
    return pd.DataFrame(rows, dtype=object)


def require_rows(name, df, cols):
    """Fail loudly when a required dimension table is unavailable.

    An empty result is almost always a Row-Level-Security refusal rather than a
    genuinely empty table: the anon key can read `picks` but not `pick_sources`.
    Proceeding would silently build features the frozen model never trained on,
    so this raises instead of degrading. Use the service-role key for full reads.
    """
    if df is None or len(df) == 0:
        raise RuntimeError(
            f"Supabase returned no rows for '{name}'. The feature builder needs this "
            "table; an empty result usually means the key in use lacks RLS access. "
            "Set SUPABASE_SERVICE_KEY to the service-role key.")
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise RuntimeError(f"Table '{name}' is missing expected column(s): {missing}")
    return df


DIMENSIONS = [
    ("leagues", "id, name, sport"),
    ("bet_types", "id, name"),
    ("capper_directory", "id, canonical_name"),
    ("pick_sources", "id, source_platform, original_message, ocr_text"),
]


def probe_table(table, col="id"):
    """One single-row request. Deliberately does NOT page: a paging probe would
    crawl the whole table and turn a cheap check into a multi-minute hang."""
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    return supabase.table(table).select(col).range(0, 0).execute().data or []


def check_access(verbose=True):
    """Preflight for the daily pipeline: verify every required table is readable.

    Returns True when the run can proceed; raises RuntimeError otherwise. One
    single-row request per table, so it costs a second or two in CI.
    """
    ok = True
    for table, cols in DIMENSIONS + [("picks", PICK_COLS)]:
        col = cols.split(",")[0].strip()
        try:
            n = len(probe_table(table, col))
            if verbose:
                print(f"  {table:<18} readable={bool(n)}")
            if not n:
                ok = False
                print(f"  !! {table}: 0 rows — the key in use likely lacks RLS access")
        except Exception as e:
            ok = False
            print(f"  !! {table}: {type(e).__name__}: {str(e)[:120]}")
    if not ok:
        raise RuntimeError(
            "Supabase preflight failed: not every required table is readable. "
            "Set SUPABASE_SERVICE_KEY (service-role) in the workflow environment.")
    return True


if __name__ == "__main__":
    print("Supabase access preflight")
    check_access()
    print("All required tables readable.")


def load_data(use_cache=True, cache_path=CACHE, verbose=True):
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    if use_cache and os.path.exists(cache_path):
        if verbose:
            print(f"Using cached picks: {cache_path}")
        picks = pd.read_parquet(cache_path)
    else:
        if verbose:
            print("Fetching picks from Supabase...")
        picks = fetch_all("picks", PICK_COLS)
        if verbose:
            print(f"  picks: {len(picks)}")
        # Cast id columns to nullable Int64: JSON bigints > 2^53 would otherwise
        # round-trip through float64 and lose precision (breaks joins on source_id).
        for c in ["id", "capper_id", "league_id", "bet_type_id", "source_id"]:
            if c in picks.columns:
                picks[c] = picks[c].astype("Int64")
        picks.to_parquet(cache_path, index=False)

    leagues = require_rows("leagues", fetch_all("leagues", "id, name, sport"), ["id", "name"])
    bet_types = require_rows("bet_types", fetch_all("bet_types", "id, name"), ["id", "name"])
    cappers = require_rows("capper_directory", fetch_all("capper_directory", "id, canonical_name"),
                           ["id", "canonical_name"])
    sources = require_rows("pick_sources",
                           fetch_all("pick_sources",
                                     "id, source_platform, original_message, ocr_text"),
                           ["id", "source_platform", "original_message", "ocr_text"])
    sources["id"] = sources["id"].astype("Int64")

    picks["pick_date"] = pd.to_datetime(picks["pick_date"], errors="coerce")
    picks = picks[picks["pick_date"].notna()].copy()
    # The picks table contains re-inserted duplicate rows (same id). Keep latest copy.
    if picks["id"].duplicated().any():
        n_dup = int(picks["id"].duplicated().sum())
        picks = picks.sort_values("created_at").drop_duplicates(subset=["id"], keep="last")
        if verbose:
            print(f"  deduped picks: removed {n_dup} duplicate rows")

    df = picks.merge(leagues.drop_duplicates(subset=["id"]).rename(
        columns={"name": "league_name", "id": "league_key"}),
        left_on="league_id", right_on="league_key", how="left")
    df = df.merge(bet_types.drop_duplicates(subset=["id"]).rename(
        columns={"name": "bet_type_name", "id": "bt_key"}),
        left_on="bet_type_id", right_on="bt_key", how="left")
    df = df.merge(cappers.drop_duplicates(subset=["id"]).rename(
        columns={"canonical_name": "capper_name", "id": "cap_key"}),
        left_on="capper_id", right_on="cap_key", how="left")
    df = df.merge(sources.drop_duplicates(subset=["id"]).rename(
        columns={"source_platform": "src_platform", "id": "src_key"}),
        left_on="source_id", right_on="src_key", how="left", suffixes=("", "_src"))

    # Discord = no site URL, or regraded rows whose URL was rewritten by the
    # regrade pipeline (they still originate from the Discord scraper).
    df["is_discord"] = (df["source_url"].isna() |
                        df["source_url"].astype(str).str.startswith("regraded_mach:")).astype(int)

    # Merge raw text: prefer picks.raw_text, fall back to pick_sources original/ocr
    text = df["raw_text"].fillna("")
    text = text.where(text != "", df["original_message"].fillna(""))
    text = text.where(text != "", df["ocr_text"].fillna(""))
    df["message"] = text

    # Outcome coding: win=1, loss=0, push excluded, pending excluded (NaN)
    res = df["result"].astype(str).str.lower().str.strip()
    df["outcome"] = np.nan
    df.loc[res.isin(["win", "won"]), "outcome"] = 1.0
    df.loc[res.isin(["loss", "lost"]), "outcome"] = 0.0
    df["dec_odds"] = df["odds_american"].apply(
        lambda o: (o / 100) + 1 if pd.notna(o) and o > 0
        else (100 / abs(o)) + 1 if pd.notna(o) and o < 0
        else 1.91
    )
    df["profit_1u"] = df["outcome"] * (df["dec_odds"] - 1) - (1 - df["outcome"])
    df["unit"] = pd.to_numeric(df["unit"], errors="coerce").fillna(1.0)
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="force live refetch")
    args = ap.parse_args()
    df = load_data(use_cache=not args.refresh)
    g = df[df["outcome"].isin([1.0, 0.0])]
    disc = g[g["is_discord"] == 1]
    print(f"rows: {len(df)} | graded: {len(g)} | discord graded: {len(disc)}")
    print(f"date range: {df['pick_date'].min().date()} -> {df['pick_date'].max().date()}")
    print("last 3 months (graded discord):")
    print(disc.groupby(disc["pick_date"].dt.to_period("M")).size().tail(3).to_string())
