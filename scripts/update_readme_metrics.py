#!/usr/bin/env python3
"""Regenerate the live numbers in the README model table.

Series 7 (RUBY) figures come from docs/ruby_forward.json, written by
ruby/forward.py in the Daily Quarry Pipeline. Series 8 (JADE) figures come
from docs/ledger/ledger_summary.json, written by v8_jade/build_site.py in
the Daily Quarry Ledger. All other rows are static history and are never
touched.

Properties:
  - idempotent: if the README already matches the ledgers, nothing changes
  - loud: a missing ledger, an unreadable field, a table whose format
    drifted, or a ledger older than 26h fails the run with ::error::
    instead of silently publishing stale numbers (that silence is how the
    Ruby page froze for 3 weeks)
  - --allow-stale skips the freshness gate for local experiments only

Usage:
  python3 scripts/update_readme_metrics.py [--readme PATH] [--allow-stale]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
RUBY_JSON = ROOT / "docs" / "ruby_forward.json"
JADE_JSON = ROOT / "docs" / "ledger" / "ledger_summary.json"

# A live ledger older than MAX_AGE_H means its producing pipeline is dead or
# its scheduled slot was skipped (GitHub cron is best-effort). 26h tolerates
# the interleaved schedules: the pipeline (09:00 UTC) reads the ledger's
# 23:30 UTC summary from the same calendar day, and the ledger (23:30 UTC)
# reads the pipeline's 09:00 UTC tracker file — each is well under 26h old.
MAX_AGE_H = 26.0
FRESH_WARN = (
    f"is older than {MAX_AGE_H:.0f}h — its producing workflow likely failed or "
    "was skipped. Fix the source pipeline; do not publish stale numbers. "
    "(Override locally with --allow-stale.)"
)


def fail(msg: str) -> "SystemExit":
    print(f"::error::update_readme_metrics: {msg}", file=sys.stderr)
    return SystemExit(1)


def parse_ts(raw: str):
    """Parse ledger timestamps: 'YYYY-MM-DD HH:MM UTC', 'YYYY-MM-DD HH:MM', 'YYYY-MM-DD'."""
    raw = raw.strip()
    for fmt in ("%Y-%m-%d %H:%M UTC", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            t = dt.datetime.strptime(raw, fmt)
            return t.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
    return None


def load_ledger(path: pathlib.Path, label: str, host: str | None, series: str, allow_stale: bool) -> dict | None:
    """Load a ledger JSON, or return None to skip that row (with a loud warning).

    Policy: the row belonging to the host workflow's own system (just written
    moments ago) must exist, parse and be fresh — any problem there is fatal.
    A foreign ledger (written by the OTHER daily workflow) that is missing or
    stale warns and skips its row instead of blocking this system's publish;
    the foreign workflow already fails its own run loudly via its own gates.
    Garbage-but-present foreign data is still fatal: that is format drift a
    human must fix.
    """
    if not path.exists():
        if host == series:
            raise fail(f"{label} not found at {path} — the host workflow just failed to write it")
        print(f"::warning::update_readme_metrics: {label} missing; SERIES {series} row left unchanged")
        return None
    try:
        d = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise fail(f"{label} is not valid JSON ({e})")

    raw = str(d.get("meta", d).get("last_update") or d.get("updated_at") or "")
    t = parse_ts(raw)
    if t is None:
        raise fail(f"{label} has no parsable last_update (got {raw!r})")
    age_h = (dt.datetime.now(dt.timezone.utc) - t).total_seconds() / 3600.0
    if allow_stale:
        print(f"update_readme_metrics: {label} age gate bypassed ({age_h:.1f}h old)")
    elif age_h > MAX_AGE_H:
        msg = f"{label} last_update={raw} ({age_h:.1f}h old) {FRESH_WARN}"
        if host == series:
            raise fail(msg)
        print(f"::warning::update_readme_metrics: {msg} SERIES {series} row left unchanged.")
        return None
    return d


def fmt_frac(x) -> str:
    """Format an ROI fraction (0.011 -> +1.1%, -1.0 -> -100.0%)."""
    return f"{float(x) * 100:+.1f}%"


def update_row(text: str, marker: str, bets: str, roi: str) -> str:
    """Rewrite the TOTAL BETS and ROI cells of the series' table row."""
    # Row shape: | **[SERIES n: NAME](url)** | ... | **<bets>** | **<roi>** |
    pat = re.compile(
        r"^(\| \*\*\[SERIES " + re.escape(marker) + r":[^\n]*"
        r"\| \*\*)([^*]+)(\*\* \| \*\*)([^*]+)(\*\* \|) *$",
        re.MULTILINE,
    )
    m = pat.search(text)
    if not m:
        raise fail(
            f"README row for SERIES {marker} not found or table format changed — "
            "update update_readme_metrics.py to match the new layout"
        )
    if m.group(2) == bets and m.group(4) == roi:
        return text
    return text[: m.start(2)] + bets + text[m.end(2) : m.start(4)] + roi + text[m.end(4) :]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--readme", default=str(README), help="README path (default: repo README.md)")
    ap.add_argument("--allow-stale", action="store_true", help="skip the freshness gate entirely (local experiments)")
    ap.add_argument("--host", choices=("ruby", "jade"), default=None,
                    help="which system hosts this run; its own ledger is strict, the foreign one warns")
    args = ap.parse_args()
    host_series = {"ruby": "7", "jade": "8"}.get(args.host)

    ruby = load_ledger(RUBY_JSON, "ruby_forward.json", host_series, "7", args.allow_stale)
    jade = load_ledger(JADE_JSON, "ledger_summary.json", host_series, "8", args.allow_stale)

    readme = pathlib.Path(args.readme)
    text = orig = readme.read_text()
    notes = []

    if ruby is not None:
        rs = ruby.get("stats", {})
        for k in ("n", "pending", "roi"):
            if rs.get(k) is None:
                raise fail(f"ruby_forward.json stats.{k} missing")
        # ruby/forward.py stores ROI as a fraction (profit_1u mean): -1.0 == -100%.
        ruby_bets, ruby_roi = str(int(rs["n"]) + int(rs["pending"])), fmt_frac(rs["roi"])
        text = update_row(text, "7", ruby_bets, ruby_roi)
        notes.append(f"S7 {ruby_bets} bets {ruby_roi}")
    else:
        notes.append("S7 row skipped (foreign ledger missing/stale)")

    if jade is not None:
        for k in ("graded", "pending", "roi_adj"):
            if k not in jade:
                raise fail(f"ledger_summary.json field '{k}' missing")
        # build_site.py stores roi_adj already percent-scaled (adj * 100).
        # No graded picks yet -> honest dash, never a fake number.
        jade_roi = "—" if jade["roi_adj"] is None else f"{float(jade['roi_adj']):+.1f}%"
        jade_bets = str(int(jade["graded"]) + int(jade["pending"]))
        text = update_row(text, "8", jade_bets, jade_roi)
        notes.append(f"S8 {jade_bets} bets {jade_roi}")
    else:
        notes.append("S8 row skipped (foreign ledger missing/stale)")

    if text != orig:
        readme.write_text(text)
        print("README metrics refreshed: " + " | ".join(notes))
    else:
        print("README metrics already current: " + " | ".join(notes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
