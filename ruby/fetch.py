"""v7 RUBY - Discord-first score-maximizing sniper.

Fetch layer: pulls all picks + supporting tables from Supabase with batching,
marks Discord-sourced picks (source_url IS NULL), and joins raw message text.
"""
import os
import time
import numpy as np
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

PICK_COLS = ("id, pick_date, pick_value, unit, odds_american, result, capper_id, "
             "league_id, bet_type_id, source_id, source_url, is_parlay, status, "
             "created_at, raw_text")


def fetch_all(supabase, table, cols="*", batch=1000, filters=None):
    rows, start = [], 0
    while True:
        q = supabase.table(table).select(cols)
        if filters:
            for f, op, v in filters:
                q = getattr(q, op)(f, v)
        data = q.range(start, start + batch - 1).execute().data
        if not data:
            break
        rows.extend(data)
        start += batch
    # dtype=object keeps bigint ids exact (avoid float64 precision loss > 2^53)
    return pd.DataFrame(rows, dtype=object)


def load_data(use_cache=True, cache_path="data/picks.parquet"):
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    if use_cache and os.path.exists(cache_path):
        print(f"Using cached picks: {cache_path}")
        picks = pd.read_parquet(cache_path)
    else:
        supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        print("Fetching picks...")
        picks = fetch_all(supabase, "picks", PICK_COLS)
        print(f"  picks: {len(picks)}")
        # Cast id columns to nullable Int64: JSON bigints > 2^53 would otherwise
        # round-trip through float64 and lose precision (breaks joins on source_id).
        for c in ["id", "capper_id", "league_id", "bet_type_id", "source_id"]:
            if c in picks.columns:
                picks[c] = picks[c].astype("Int64")
        picks.to_parquet(cache_path, index=False)
    leagues = fetch_all(create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]),
                        "leagues", "id, name, sport")
    bet_types = fetch_all(create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]),
                          "bet_types", "id, name")
    cappers = fetch_all(create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]),
                        "capper_directory", "id, canonical_name")
    sources = fetch_all(create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]),
                        "pick_sources", "id, source_platform, original_message, ocr_text")
    sources["id"] = sources["id"].astype("Int64")

    picks["pick_date"] = pd.to_datetime(picks["pick_date"], errors="coerce")
    picks = picks[picks["pick_date"].notna()].copy()
    # The picks table contains re-inserted duplicate rows (same id). Keep latest copy.
    if picks["id"].duplicated().any():
        n_dup = int(picks["id"].duplicated().sum())
        picks = picks.sort_values("created_at").drop_duplicates(subset=["id"], keep="last")
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

    # Merge raw text: prefer picks.raw_text, fall back to pick_sources.original_message / ocr_text
    text = df["raw_text"].fillna("")
    text = text.where(text != "", df["original_message"].fillna(""))
    text = text.where(text != "", df["ocr_text"].fillna(""))
    df["message"] = text

    # Outcome coding: win=1, loss=0, push excluded, pending excluded
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
