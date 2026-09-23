"""THE QUARRY LEDGER - site builder.

Assembles the public, self-contained website from live artifacts:
  - forward_ledger.json          (daily forward test)
  - models/fold_probs.parquet    (walk-forward cache -> evidence visuals)
  - models/jade_all.json         (feature importances)
  - models/jade_policy.json      (frozen policy metadata)

Usage: python3 v8_jade/build_site.py
Writes: v8_jade/site/index.html  (single file, no build step, GitHub-Pages ready)
"""
import os
import sys
import json
import pickle
import argparse
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import grade_picks, profit_vector

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "site")
BAND = (1.80, 2.00)
TUNE_CUT = pd.Timestamp("2026-09-01")

IVORY = "#EDE7D6"
GOLD = "#C6A962"
JADE = "#43A37C"
OX = "#B4654A"
FAINT = "#6E6A5E"


def v6_select(fd):
    s = fd[fd["odds_american"].notna()]
    s = s[(s["dec_odds"] >= BAND[0]) & (s["dec_odds"] <= BAND[1])]
    s = s[s["cnt_30d"] >= 5]
    s = s[s["shrunk_acc_lt"] >= 0.55]
    s = s.sort_values(["pick_date", "prob_all_cal", "prob_all"], ascending=[True, False, False])
    return s.groupby("pick_date", sort=False).head(5)


def daily_equity(sel):
    d = sel[sel["outcome"].isin([1.0, 0.0])].sort_values("pick_date")
    if d.empty:
        return []
    pv = profit_vector(d)
    df = pd.DataFrame({"d": d["pick_date"].values, "p": pv})
    daily = df.groupby("d")["p"].sum().cumsum()
    return [(str(pd.Timestamp(k).date()), round(float(v), 2)) for k, v in daily.items()]


def polyline_svg(points, w=1000, h=340, pad_l=58, pad_r=20, pad_t=24, pad_b=40,
                 split_at=None, split_colors=("#3E8F6E", GOLD)):
    """Equity curve as SVG. split_at: index where holdout starts (color change)."""
    if not points:
        return '<svg viewBox="0 0 1000 340"><text x="500" y="170" text-anchor="middle" fill="#6E6A5E">no data yet</text></svg>'
    ys = [v for _, v in points]
    ymin, ymax = min(min(ys), 0), max(max(ys), 0)
    pad = (ymax - ymin) * 0.08 or 1
    ymin, ymax = ymin - pad, ymax + pad
    n = len(points)
    xs = [pad_l + i / max(n - 1, 1) * (w - pad_l - pad_r) for i in range(n)]

    def Y(v):
        return pad_t + (ymax - v) / (ymax - ymin) * (h - pad_t - pad_b)

    parts = [f'<svg viewBox="0 0 {w} {h}" class="chart">']
    # gridlines
    for g in np.linspace(ymin, ymax, 5):
        gy = Y(g)
        parts.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{w-pad_r}" y2="{gy:.1f}" class="grid"/>')
        parts.append(f'<text x="{pad_l-10}" y="{gy+4:.1f}" class="tick" text-anchor="end">{g:+.0f}u</text>')
    if ymin < 0 < ymax:
        parts.append(f'<line x1="{pad_l}" y1="{Y(0):.1f}" x2="{w-pad_r}" y2="{Y(0):.1f}" class="zero"/>')
    # split segments
    segs = [(0, split_at or n, split_colors[0])]
    if split_at:
        segs.append((max(split_at - 1, 0), n, split_colors[1]))
    for a, b, color in segs:
        pts = " ".join(f"{xs[i]:.1f},{Y(points[i][1]):.1f}" for i in range(a, b))
        parts.append(f'<polyline class="draw" points="{pts}" fill="none" stroke="{color}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>')
    if split_at:
        hx = xs[split_at]
        parts.append(f'<line x1="{hx:.1f}" y1="{pad_t}" x2="{hx:.1f}" y2="{h-pad_b}" class="split"/>')
        parts.append(f'<text x="{hx+8:.1f}" y="{pad_t+14}" class="tick gold">HOLDOUT ▸</text>')
    # x labels (first/quarter/mid/3q/last)
    for i in {0, n // 4, n // 2, 3 * n // 4, n - 1}:
        parts.append(f'<text x="{xs[i]:.1f}" y="{h-12}" class="tick" text-anchor="middle">{points[i][0][5:]}</text>')
    parts.append("</svg>")
    return "".join(parts)


def bars_svg(months, w=1000, h=260):
    """months: list of (label, adj, n, grade). Vertical engraved bars."""
    if not months:
        return '<svg viewBox="0 0 1000 260"></svg>'
    vals = [v for _, v, _, _ in months]
    vmax = max(max(vals), 0.01)
    vmin = min(min(vals), -0.01)
    span = vmax - vmin
    pad_t, pad_b, pad_l, pad_r = 30, 46, 40, 20
    bw = (w - pad_l - pad_r) / len(months)
    zero_y = pad_t + (vmax / span) * (h - pad_t - pad_b)

    def Y(v):
        return pad_t + (vmax - v) / span * (h - pad_t - pad_b)

    parts = [f'<svg viewBox="0 0 {w} {h}" class="chart">']
    parts.append(f'<line x1="{pad_l}" y1="{zero_y:.1f}" x2="{w-pad_r}" y2="{zero_y:.1f}" class="zero"/>')
    for i, (label, v, n, g) in enumerate(months):
        cx = pad_l + i * bw + bw / 2
        y0, y1 = zero_y, Y(v)
        color = JADE if v >= 0 else OX
        parts.append(f'<rect x="{cx-bw*0.26:.1f}" y="{min(y0,y1):.1f}" width="{bw*0.52:.1f}" height="{max(abs(y1-y0),2):.1f}" fill="{color}" class="grow" style="transform-origin:{cx-bw*0.26:.1f}px {zero_y:.1f}px" rx="2"/>')
        vy = (min(y0, y1) - 8) if v >= 0 else (max(y0, y1) + 18)
        parts.append(f'<text x="{cx:.1f}" y="{vy:.1f}" class="tick" text-anchor="middle">{v*100:+.1f}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{h-24}" class="tick" text-anchor="middle">{label}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{h-8}" class="tick faint" text-anchor="middle">n={n} · {g}</text>')
    parts.append("</svg>")
    return "".join(parts)


def feat_svg(feats, w=1000, h=300):
    if not feats:
        return '<svg viewBox="0 0 1000 300"></svg>'
    pad_l, pad_r, pad_t, pad_b = 240, 80, 14, 14
    vmax = max(v for _, v in feats) or 1
    bh = (h - pad_t - pad_b) / len(feats)
    parts = [f'<svg viewBox="0 0 {w} {h}" class="chart">']
    for i, (name, gain) in enumerate(feats):
        cy = pad_t + i * bh + bh / 2
        bwid = (gain / vmax) * (w - pad_l - pad_r)
        parts.append(f'<rect x="{pad_l}" y="{cy-bh*0.28:.1f}" width="{bwid:.1f}" height="{bh*0.56:.1f}" fill="{GOLD}" opacity="0.85" rx="2" class="growx" style="transform-origin:{pad_l}px {cy:.1f}px"/>')
        parts.append(f'<text x="{pad_l-12}" y="{cy+4:.1f}" class="tick" text-anchor="end">{name}</text>')
        parts.append(f'<text x="{pad_l+bwid+10:.1f}" y="{cy+4:.1f}" class="tick faint">{gain:.0f}</text>')
    parts.append("</svg>")
    return "".join(parts)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def fmt_odds(o):
    if o is None:
        return "—"
    return f"+{int(o)}" if o > 0 else str(int(o))


def mock_ledger():
 """Realistic populated ledger for design preview ONLY (never written to disk)."""
 P = lambda id,d,c,l,pk,o,prob,res: {"id":id,"pick_date":d,"capper":c,"league":l,"pick":pk,
   "odds_american":o,"prob":prob,"shrunk_acc_lt":0.561,"added_at":"","result":res}
 return {
  "policy_version": "v8-jade-1.1", "features_version": "jade-1",
  "start_date": "2026-09-15", "updated_at": "2026-09-23 08:31",
  "summary": {"graded": 15, "pending": 5, "pushes": 0, "profit": 3.0,
              "roi": 0.033, "adj_roi": 0.033, "grade": "B+"},
  "picks": [
   P("m01","2026-09-15","Ben Burns","NFL","Ravens -4.5 vs Browns",-110,0.589,"WIN"),
   P("m02","2026-09-15","Ydc","MLB","Phillies ML vs Marlins",-115,0.578,"WIN"),
   P("m03","2026-09-15","Prosportspicks","MLB","Yankees vs Red Sox Over 8.5",-105,0.572,"LOSS"),
   P("m04","2026-09-16","Cashitbaby","NFL","Chiefs -2.5 vs Chargers",-110,0.595,"WIN"),
   P("m05","2026-09-16","Ricky Tran","NFL","Bills vs Dolphins Under 44.5",-110,0.581,"WIN"),
   P("m06","2026-09-16","Shark Culture","MLB","Astros ML vs Mariners",+100,0.568,"LOSS"),
   P("m07","2026-09-17","Ben Burns","NFL","49ers -3 vs Rams",-110,0.601,"WIN"),
   P("m08","2026-09-17","Exclusive Play","NHL","Maple Leafs ML vs Bruins",-105,0.574,"LOSS"),
   P("m09","2026-09-18","Ydc","NFL","Packers -1.5 vs Titans",-115,0.586,"WIN"),
   P("m10","2026-09-18","Prosportspicks","MLB","Dodgers vs Rockies Over 9",-110,0.571,"WIN"),
   P("m11","2026-09-19","Ben Burns","NFL","Texans -2.5 vs Jaguars",-110,0.592,"WIN"),
   P("m12","2026-09-19","Cashitbaby","MLB","Braves ML vs Mets",-120,0.583,"LOSS"),
   P("m13","2026-09-20","Ricky Tran","NFL","Vikings vs Bengals Over 40.5",-110,0.577,"WIN"),
   P("m14","2026-09-20","Shark Culture","NFL","Broncos ML vs Raiders",+100,0.569,"LOSS"),
   P("m15","2026-09-21","Ben Burns","NFL","Cowboys -3 vs Bears",-110,0.598,"WIN"),
   P("m16","2026-09-23","Ben Burns","NFL","Falcons -1.5 vs Panthers",-110,0.604,"PENDING"),
   P("m17","2026-09-23","Ydc","MLB","Orioles ML vs Red Sox",-110,0.591,"PENDING"),
   P("m18","2026-09-23","Prosportspicks","NFL","Jets vs Patriots Under 38.5",-105,0.587,"PENDING"),
   P("m19","2026-09-23","Cashitbaby","MLB","Tigers ML vs Guardians",+100,0.583,"PENDING"),
   P("m20","2026-09-23","Exclusive Play","NHL","Lightning ML vs Panthers",-115,0.579,"PENDING"),
  ]}


def main():
    # ---------- gather data ----------
    fp_path = os.path.join(BASE, "models", "fold_probs.parquet")
    if os.path.exists(fp_path):
        fd = pd.read_parquet(fp_path)
        fd["pick_date"] = pd.to_datetime(fd["pick_date"])
        site = v6_select(fd)
        tune, hold = site[site["pick_date"] < TUNE_CUT], site[site["pick_date"] >= TUNE_CUT]
        sc_tune, sc_hold = grade_picks(tune), grade_picks(hold)
        months = []
        for m, g in site.groupby(site["pick_date"].dt.to_period("M")):
            s = grade_picks(g)
            months.append((str(m)[5:], s["adj_roi"], s["n"], s["grade"]))  # "03" style
        eq_tune, eq_hold = daily_equity(tune), daily_equity(hold)
        all_eq = eq_tune + eq_hold
        split_idx = len(eq_tune)
        eq_svg = polyline_svg(all_eq, split_at=split_idx)
        bars = bars_svg(months)
        month_rows = [(str(m), s["adj_roi"], s["n"], s["profit"], s["grade"])
                      for m, s in [(m, grade_picks(g)) for m, g in site.groupby(site["pick_date"].dt.to_period("M"))]]
        hold_pv = profit_vector(hold)
        dd = float(np.min(np.minimum.accumulate(np.cumsum(hold_pv)))) if len(hold_pv) else 0.0
    else:
        # graceful degradation: evidence section renders placeholders
        fd, site = None, None
        sc_hold = {"adj_roi": None, "roi": None, "n": 0, "wr": None}
        months = []
        month_rows = []
        eq_svg = polyline_svg([])
        bars = bars_svg([])
        dd = 0.0

    import xgboost as xgb
    ma = xgb.Booster()
    ma.load_model(os.path.join(BASE, "models", "jade_all.json"))
    gain = sorted(ma.get_score(importance_type="gain").items(), key=lambda t: -t[1])[:8]
    feats = feat_svg(gain)

    lp = os.path.join(BASE, "forward_ledger.json")
    ledger = json.load(open(lp)) if os.path.exists(lp) else {}
    summary = ledger.get("summary", {})
    picks = ledger.get("picks", [])

    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true",
                    help="design preview with a populated mock ledger (nothing written to real ledger)")
    ap.add_argument("--out", default=None, help="override output path")
    args = ap.parse_args()
    if args.mock:
        ledger = mock_ledger()
        summary = ledger["summary"]
        picks = ledger["picks"]

    start = ledger.get("start_date", "—")
    n_graded, n_pend = summary.get("graded", 0), summary.get("pending", 0)
    profit = summary.get("profit", 0.0)
    adj = summary.get("adj_roi")
    grade = summary.get("grade", "—")
    day_n = 1 if start == "—" else max((pd.Timestamp.now().normalize() - pd.Timestamp(start)).days + 1, 1)
    confirm = min(n_graded, 100)

    ticker_items = [f"{p.get('capper','?').upper()} · {p.get('league','?')} · {p.get('odds_american') or '—'} · {p['result']}"
                    for p in sorted(picks, key=lambda x: x["pick_date"])[-12:]] or \
        ["BAND 1.80–2.00", "CAP 5/DAY", "SKILL ≥ .55", "FLAT 1 UNIT", "MODEL FROZEN", "LEDGER IS THE REFEREE"]

    # ---------- html ----------
    grade_display = grade if grade != "-" else "—"
    grade_caption = "awaiting first verdict" if grade == "-" else f"capperstracked grade · day {day_n}"
    adj_display = "—" if adj is None else f"{adj:+.1%}"

    css = """
:root{--bg:#0B0E0C;--ink:#101512;--panel:#12171399;--ivory:#EDE7D6;--ivory-dim:#B9B29F;
--gold:#C6A962;--gold-pale:#E2CE9C;--jade:#43A37C;--ox:#B4654A;--hair:rgba(198,169,98,.22);
--hair2:rgba(237,231,214,.09);--serif:'Fraunces',Georgia,'Times New Roman',serif;
--mono:'IBM Plex Mono',ui-monospace,Menlo,monospace}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--ivory);font-family:var(--serif);
font-optical-sizing:auto;-webkit-font-smoothing:antialiased;overflow-x:hidden}
::selection{background:var(--gold);color:#0B0E0C}
.grain{position:fixed;inset:0;z-index:40;pointer-events:none;opacity:.05;
background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.6'/%3E%3C/svg%3E")}
.wrap{max-width:1080px;margin:0 auto;padding:0 28px}
section{padding:84px 0;border-top:1px solid var(--hair2)}
.kicker{font-family:var(--mono);font-size:11px;letter-spacing:.34em;text-transform:uppercase;
color:var(--gold);display:flex;align-items:center;gap:14px;margin-bottom:26px}
.kicker::after{content:'';height:1px;background:var(--hair);flex:1;max-width:220px}
h2{font-size:clamp(30px,4.4vw,46px);font-weight:390;letter-spacing:-.015em;line-height:1.04;margin-bottom:14px}
h2 em{font-style:italic;color:var(--gold-pale);font-weight:340}
.lede{color:var(--ivory-dim);font-size:16.5px;line-height:1.65;max-width:640px;font-weight:350}
/* masthead */
.mast{padding:30px 0 0;border-bottom:1px solid var(--hair)}
.mast-top{display:flex;justify-content:space-between;align-items:center;
font-family:var(--mono);font-size:10.5px;letter-spacing:.3em;color:var(--ivory-dim);
text-transform:uppercase;padding-bottom:22px;border-bottom:1px solid var(--hair2)}
.livedot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--jade);
margin-right:9px;animation:pulse 2.4s ease-in-out infinite}
.mast-top .mast-link{color:var(--gold);text-decoration:none;border-bottom:1px solid transparent;
transition:border-color .3s ease,color .3s ease}
.mast-top .mast-link:hover{color:var(--gold-pale);border-bottom-color:var(--gold-pale)}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(67,163,124,.5)}50%{box-shadow:0 0 0 6px rgba(67,163,124,0)}}
.tickerclip{overflow:hidden;border-bottom:1px solid var(--hair2);background:var(--ink)}
.ticker{display:inline-flex;gap:56px;white-space:nowrap;padding:11px 0;
font-family:var(--mono);font-size:11px;letter-spacing:.18em;color:var(--ivory-dim);
animation:slide 42s linear infinite}
.ticker span b{color:var(--gold-pale);font-weight:500}
.ticker span i{font-style:normal}.ticker .w{color:var(--jade)}.ticker .l{color:var(--ox)}
@keyframes slide{to{transform:translateX(-50%)}}
/* hero */
.hero{padding:88px 0 72px;position:relative}
.hero h1{font-size:clamp(52px,9vw,124px);line-height:.94;font-weight:420;letter-spacing:-.03em}
.hero h1 .w{display:inline-block;overflow:hidden;vertical-align:bottom}
.hero h1 .w i{display:inline-block;font-style:normal;transform:translateY(110%);
animation:rise .9s cubic-bezier(.2,.7,.2,1) forwards}
.hero h1 .w:nth-child(2) i{animation-delay:.12s}.hero h1 .w:nth-child(3) i{animation-delay:.24s}
@keyframes rise{to{transform:translateY(0)}}
.hero .series{font-family:var(--mono);font-size:11.5px;letter-spacing:.4em;color:var(--gold);
text-transform:uppercase;margin:26px 0 18px;animation:fade 1.2s .5s both}
.hero p.sub{max-width:560px;color:var(--ivory-dim);font-size:17.5px;line-height:1.6;
font-weight:350;font-style:italic;animation:fade 1.2s .7s both}
@keyframes fade{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.hero-grid{display:grid;grid-template-columns:1fr auto;gap:40px;align-items:end}
/* medallion */
.medal{position:relative;width:210px;height:210px;animation:fade 1.2s .9s both}
.medal svg{width:100%;height:100%}
.medal .ring{animation:spin 80s linear infinite;transform-origin:50% 50%}
@keyframes spin{to{transform:rotate(360deg)}}
.medal .grade{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;
justify-content:center;text-align:center}
.medal .grade b{font-size:64px;font-weight:430;color:var(--gold-pale);letter-spacing:-.02em}
.medal .grade span{font-family:var(--mono);font-size:9px;letter-spacing:.26em;
text-transform:uppercase;color:var(--ivory-dim);max-width:130px;line-height:1.7}
/* figures */
.figs{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--hair2);
border:1px solid var(--hair2);margin-top:64px}
.fig{background:var(--bg);padding:26px 26px 22px;position:relative}
.fig b{display:block;font-size:34px;font-weight:420;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.fig span{font-family:var(--mono);font-size:9.5px;letter-spacing:.28em;text-transform:uppercase;
color:var(--ivory-dim);display:block;margin-top:8px}
.fig::after{content:'';position:absolute;left:26px;right:26px;bottom:0;height:2px;background:var(--gold);
transform:scaleX(0);transform-origin:left;transition:transform .8s cubic-bezier(.2,.7,.2,1)}
.fig.in::after{transform:scaleX(1)}
/* slate empty state */
.slate-empty{border:1px solid var(--hair);padding:64px 40px;text-align:center;position:relative;overflow:hidden}
.slate-empty .dia{width:54px;height:54px;margin:0 auto 26px;display:block}
.slate-empty .dia path{fill:none;stroke:var(--gold);stroke-width:1.4;
stroke-dasharray:220;stroke-dashoffset:220;animation:draw 2.4s ease forwards}
@keyframes draw{to{stroke-dashoffset:0}}
.slate-empty h3{font-size:26px;font-weight:400;font-style:italic;color:var(--gold-pale);margin-bottom:12px}
.slate-empty p{color:var(--ivory-dim);font-size:15px;max-width:440px;margin:0 auto;line-height:1.65}
/* day dial */
.dialbar{display:flex;align-items:center;gap:18px;margin-top:22px;font-family:var(--mono);
font-size:10.5px;letter-spacing:.22em;color:var(--ivory-dim);text-transform:uppercase}
.dialbar .track{flex:1;height:1px;background:var(--hair2);position:relative}
.dialbar .fill{position:absolute;left:0;top:0;height:1px;background:var(--gold);transition:width 1.4s ease}
/* method */
.method{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--hair2);border:1px solid var(--hair2)}
.principle{background:var(--bg);padding:40px 38px 44px;transition:background .5s}
.principle:hover{background:var(--ink)}
.principle .num{font-size:15px;color:var(--gold);font-family:var(--mono);letter-spacing:.3em}
.principle h3{font-size:23px;font-weight:420;margin:16px 0 12px;letter-spacing:-.01em}
.principle p{color:var(--ivory-dim);font-size:14.5px;line-height:1.7;font-weight:350}
.principle svg{margin-top:22px}
/* certificate */
.cert{border:1px solid var(--hair);position:relative;padding:0;overflow:hidden}
.cert-top{display:flex;justify-content:space-between;padding:18px 26px;
font-family:var(--mono);font-size:10px;letter-spacing:.3em;text-transform:uppercase;
color:var(--ivory-dim);border-bottom:1px solid var(--hair2)}
.cert-body{display:grid;grid-template-columns:repeat(4,1fr)}
.cert-body .cell{padding:34px 26px;border-right:1px solid var(--hair2)}
.cert-body .cell:last-child{border-right:0}
.cert-body b{font-size:clamp(26px,3vw,38px);font-weight:420;letter-spacing:-.02em}
.cert-body span{display:block;font-family:var(--mono);font-size:9.5px;letter-spacing:.26em;
text-transform:uppercase;color:var(--ivory-dim);margin-top:10px}
.stamp{position:absolute;right:26px;top:64px;transform:rotate(-8deg);border:2px solid var(--jade);
color:var(--jade);font-family:var(--mono);font-size:10px;letter-spacing:.3em;padding:9px 14px;
text-transform:uppercase;border-radius:3px;opacity:.9;animation:stamp .5s 1.1s cubic-bezier(.2,2,.4,1) both}
@keyframes stamp{from{opacity:0;transform:rotate(-8deg) scale(1.6)}to{opacity:.9;transform:rotate(-8deg) scale(1)}}
/* charts */
.chart{width:100%;height:auto;background:transparent}
.chart .grid{stroke:var(--hair2);stroke-width:1}
.chart .zero{stroke:rgba(237,231,214,.25);stroke-width:1;stroke-dasharray:3 4}
.chart .split{stroke:var(--hair);stroke-width:1;stroke-dasharray:2 5}
.chart .tick{fill:var(--ivory-dim);font-family:var(--mono);font-size:11px;letter-spacing:.06em}
.chart .tick.gold{fill:var(--gold)}
.chart .tick.faint{fill:var(--ivory-dim);opacity:.65}
html.js .draw{stroke-dasharray:2400;stroke-dashoffset:2400;transition:stroke-dashoffset 2.6s cubic-bezier(.4,0,.2,1)}
html.js .in .draw{stroke-dashoffset:0}
html.js .grow{transform:scaleY(0);transition:transform 1s cubic-bezier(.2,.7,.2,1)}
html.js .in .grow{transform:scaleY(1)}
html.js .growx{transform:scaleX(0);transition:transform 1s cubic-bezier(.2,.7,.2,1)}
html.js .in .growx{transform:scaleX(1)}
/* gates table */
table.ledger-t{width:100%;border-collapse:collapse;font-size:14.5px}
.ledger-t th{font-family:var(--mono);font-size:9.5px;letter-spacing:.28em;text-transform:uppercase;
color:var(--ivory-dim);text-align:left;padding:14px 16px;border-bottom:1px solid var(--hair)}
.ledger-t td{padding:17px 16px;border-bottom:1px solid var(--hair2);font-weight:350;color:var(--ivory)}
.ledger-t td.mono{font-family:var(--mono);font-size:12.5px;letter-spacing:.05em;color:var(--ivory-dim)}
.chip{display:inline-block;font-family:var(--mono);font-size:9.5px;letter-spacing:.22em;
padding:5px 10px;border-radius:2px;text-transform:uppercase;border:1px solid}
.chip.pass{color:var(--jade);border-color:rgba(67,163,124,.5)}
.chip.fail{color:var(--ox);border-color:rgba(180,101,74,.5)}
.chip.bline{color:var(--gold);border-color:var(--hair)}
.chip.w{color:var(--jade);border-color:rgba(67,163,124,.5)}
.chip.l{color:var(--ox);border-color:rgba(180,101,74,.5)}
.chip.p{color:var(--gold-pale);border-color:var(--hair)}
.slate-day{font-family:var(--mono);font-size:10px;letter-spacing:.3em;color:var(--ivory-dim);
text-transform:uppercase;margin:34px 0 4px}
/* risk */
.risk{columns:2;column-gap:48px;font-size:13.5px;line-height:1.75;color:var(--ivory-dim);font-weight:350}
.risk p{break-inside:avoid;margin-bottom:18px}
.risk b{color:var(--ivory);font-weight:450}
/* footer */
footer{border-top:1px solid var(--hair);padding:44px 0 60px;font-family:var(--mono);
font-size:10.5px;letter-spacing:.2em;color:var(--ivory-dim);text-transform:uppercase;
display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}
html.js [data-reveal]{opacity:0;transform:translateY(16px);transition:opacity .9s ease,transform .9s cubic-bezier(.2,.7,.2,1)}
html.js [data-reveal].in{opacity:1;transform:none}
@media (max-width:860px){.hero-grid{grid-template-columns:1fr}.figs{grid-template-columns:repeat(2,1fr)}
.method{grid-template-columns:1fr}.cert-body{grid-template-columns:repeat(2,1fr)}
.cert-body .cell{border-bottom:1px solid var(--hair2)}.risk{columns:1}.medal{margin:14px auto 0}
.mast-top .mast-link{display:none}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}
html.js .draw{stroke-dashoffset:0}html.js .grow,html.js .growx{transform:none}html.js [data-reveal]{opacity:1;transform:none}}
"""

    seal = """<svg viewBox="0 0 200 200" fill="none">
  <g class="ring">
    <circle cx="100" cy="100" r="94" stroke="#C6A962" stroke-opacity=".55" stroke-width="1"/>
    <circle cx="100" cy="100" r="86" stroke="#C6A962" stroke-opacity=".3" stroke-width=".6" stroke-dasharray="2 6"/>
    <g fill="#C6A962" font-family="IBM Plex Mono,monospace" font-size="9" letter-spacing="4">
      <text x="100" y="14" text-anchor="middle" fill-opacity=".8">◆</text>
      <text x="100" y="194" text-anchor="middle" fill-opacity=".8">◆</text>
      <text x="12" y="104" text-anchor="middle" fill-opacity=".8">◆</text>
      <text x="188" y="104" text-anchor="middle" fill-opacity=".8">◆</text>
    </g>
  </g>
  <circle cx="100" cy="100" r="66" stroke="#C6A962" stroke-opacity=".45" stroke-width="1"/>
  <path d="M100 58 L134 100 L100 142 L66 100 Z" stroke="#43A37C" stroke-opacity=".7" stroke-width="1.1" fill="none"/>
</svg>"""

    ticker_html = "".join(
        f'<span>{"<b>◆</b> "}{esc(t)}</span>' for t in (ticker_items * 2))
    month_cells = "".join(
        f'<tr><td>{m}</td><td class="mono">{n}</td><td class="mono">{adj*100:+.1f}%</td>'
        f'<td class="mono">{p:+.1f}u</td><td class="mono">{g}</td></tr>'
        for m, adj, n, p, g in month_rows)

    # ---------- slate rendering (open orders; quiet state only when none) ----------
    # Every still-ungraded order is shown, not just those dated today: the upstream
    # feed delivers a day's picks with a lag, so a build just after midnight UTC
    # would otherwise render a live ledger as "quiet" while orders sat open.
    today = pd.Timestamp.now().normalize()
    slate_rows = sorted([p for p in picks if p["result"] == "PENDING"],
                        key=lambda x: (pd.Timestamp(x["pick_date"]), float(x.get("prob") or 0)),
                        reverse=True)[:12]
    slate_dates = sorted({str(pd.Timestamp(p["pick_date"]).date()) for p in slate_rows})
    slate_is_today = slate_dates == [str(today.date())]

    if not slate_rows:
        slate_head, slate_head_em = "Today’s", "orders."
        slate_lede = ("Each morning the frozen model surveys every posted price and returns at most "
                      "five orders. They are carved here before the games begin — then the ledger does the talking.")
    elif slate_is_today:
        slate_head, slate_head_em = "Today’s", "orders."
        slate_lede = ("Each morning the frozen model surveys every posted price and returns at most "
                      "five orders. They are carved here before the games begin — then the ledger does the talking.")
    else:
        slate_head, slate_head_em = "Open", "orders."
        slate_lede = ("Orders still awaiting a verdict. The upstream feed publishes each day’s picks with a "
                      f"lag, so these ungraded orders span {esc(slate_dates[0])}–{esc(slate_dates[-1])}. "
                      "Prices are the numbers posted at selection; nothing is added after the fact.")
    recent_rows = sorted([p for p in picks if p["result"] in ("WIN", "LOSS", "PUSH")],
                         key=lambda x: x["pick_date"])[-10:][::-1]

    date_head = "" if slate_is_today else "<th>Date</th>"

    def slate_row(p):
        chip = {"WIN": "w", "LOSS": "l", "PENDING": "p", "PUSH": "p"}.get(p["result"], "p")
        date_cell = "" if slate_is_today else \
            f'<td class="mono">{esc(str(pd.Timestamp(p["pick_date"]).date()))}</td>'
        return (f'<tr>{date_cell}<td>{esc(p.get("capper","?"))}</td><td class="mono">{esc(p.get("league","?"))}</td>'
                f'<td>{esc(str(p.get("pick",""))[:44])}</td><td class="mono">{fmt_odds(p.get("odds_american"))}</td>'
                f'<td class="mono">{p.get("prob",0):.3f}</td>'
                f'<td><span class="chip {chip}">{esc(p["result"])}</span></td></tr>')

    if slate_rows:
        slate_html = ("<table class=\"ledger-t\">"
                      f"<tr>{date_head}<th>Capper</th><th>League</th><th>Pick</th><th>Price</th><th>Model</th><th>Verdict</th></tr>"
                      + "".join(slate_row(p) for p in slate_rows) + "</table>")
    else:
        slate_html = ('<div class="slate-empty">'
                      '<svg class="dia" viewBox="0 0 54 54"><path d="M27 4 L50 27 L27 50 L4 27 Z"/></svg>'
                      '<h3>The quarry is quiet.</h3>'
                      f'<p>{"The ledger opened " + esc(str(start)) + ". First verdicts are due within the day; the slate for tomorrow is cut at first light. Nothing is ever added after the fact."}</p></div>')

    def verdict_chip(p):
        cls = {"WIN": "w", "LOSS": "l", "PUSH": "p"}.get(p["result"], "p")
        return f'<span class="chip {cls}">{esc(p["result"])}</span>'

    if recent_rows:
        recent_html = ("<table class=\"ledger-t\">"
                       "<tr><th>Date</th><th>Capper</th><th>Pick</th><th>Price</th><th>Verdict</th></tr>"
                       + "".join(
                           f'<tr><td class="mono">{p["pick_date"][5:]}</td><td>{esc(p.get("capper","?"))}</td>'
                           f'<td>{esc(str(p.get("pick",""))[:44])}</td><td class="mono">{fmt_odds(p.get("odds_american"))}</td>'
                           f'<td>{verdict_chip(p)}</td></tr>'
                           for p in recent_rows) + "</table>")
    else:
        recent_html = ""

    html_doc = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Quarry Ledger — Series VIII · JADE</title>
<meta name="description" content="A frozen model, one unit at a time. Public forward ledger of the JADE selection system.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..600;1,9..144,300..600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{css}</style></head>
<body><div class="grain"></div>

<header class="mast">
  <div class="wrap mast-top">
    <span><span class="livedot"></span>Ledger open · day {day_n}</span>
    <span>Quarry Intelligence · Assay House</span>
    <a class="mast-link" href="../web/selector.html">← Control Center</a>
    <span>Est. {esc(str(start))}</span>
  </div>
  <div class="tickerclip"><div class="ticker">{ticker_html}</div></div>
</header>

<section class="hero">
  <div class="wrap hero-grid">
    <div>
      <h1><span class="w"><i>The</i></span> <span class="w"><i>Quarry</i></span> <span class="w"><i>Ledger.</i></span></h1>
      <div class="series">Series VIII · Jade · A public forward test</div>
      <p class="sub">One frozen model. Five picks a day, one unit each, carved into a public ledger
      every morning. Nothing re-tuned, nothing hidden — results land here exactly as they fall.</p>
    </div>
    <div class="medal">{seal}<div class="grade"><b>{esc(str(grade_display))}</b><span>{esc(grade_caption)}</span></div></div>
  </div>
  <div class="wrap">
    <div class="figs">
      <div class="fig" data-reveal><b data-count="{n_graded}">{n_graded}</b><span>Picks graded</span></div>
      <div class="fig" data-reveal><b data-count="{n_pend}">{n_pend}</b><span>Awaiting verdict</span></div>
      <div class="fig" data-reveal><b>{profit:+.1f}u</b><span>Ledger profit</span></div>
      <div class="fig" data-reveal><b>{adj_display}</b><span>Adjusted ROI</span></div>
    </div>
    <div class="dialbar"><span>0</span>
      <div class="track"><div class="fill" style="width:{confirm}%"></div></div>
      <span>{n_graded} / 100 · confirmation assay</span></div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="kicker">The Slate</div>
    <h2>{slate_head} <em>{slate_head_em}</em></h2>
    <p class="lede">{slate_lede}</p>
    <div style="margin-top:36px" data-reveal>{slate_html}</div>
    <div class="dialbar"><span>0</span>
      <div class="track"><div class="fill" style="width:{confirm}%"></div></div>
      <span>{n_graded} / 100 · confirmation assay</span></div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="kicker">The Method</div>
    <h2>Four rules, <em>carved once.</em></h2>
    <p class="lede">Every prior series learned the same lesson: edges die from tinkering. Jade is
    governed by four fixed rules and a public referee.</p>
    <div class="method" style="margin-top:40px">
      <div class="principle" data-reveal>
        <div class="num">I</div><h3>The Skill Gate</h3>
        <p>A capper’s lifetime record, shrunk toward the market’s −5% prior (k = 24), must clear
        a .55 win rate before any pick is considered. Hot streaks don’t clear it. Proven edge does.</p>
        <svg width="120" height="10"><line x1="0" y1="5" x2="120" y2="5" stroke="#C6A962" stroke-opacity=".4"/><circle cx="96" cy="5" r="3.5" fill="#43A37C"/></svg>
      </div>
      <div class="principle" data-reveal>
        <div class="num">II</div><h3>The Band</h3>
        <p>Only prices between 1.80 and 2.00 decimal (−125 to −100). Blind money loses in every
        band to the vig; this is where the model’s skill selection converts best.</p>
        <svg width="120" height="10"><line x1="0" y1="5" x2="120" y2="5" stroke="#C6A962" stroke-opacity=".4"/><line x1="24" y1="1" x2="24" y2="9" stroke="#C6A962"/><line x1="96" y1="1" x2="96" y2="9" stroke="#C6A962"/></svg>
      </div>
      <div class="principle" data-reveal>
        <div class="num">III</div><h3>The Cap</h3>
        <p>Five orders a day, flat one unit, no parlays, no chasing, no doubling after losses.
        Volume is capped by rule, not by mood — the grade rewards discipline, not action.</p>
        <svg width="120" height="10"><line x1="0" y1="5" x2="120" y2="5" stroke="#C6A962" stroke-opacity=".4"/><g fill="#C6A962"><rect x="20" y="1" width="6" height="8"/><rect x="34" y="1" width="6" height="8"/><rect x="48" y="1" width="6" height="8"/><rect x="62" y="1" width="6" height="8"/><rect x="76" y="1" width="6" height="8"/></g></svg>
      </div>
      <div class="principle" data-reveal>
        <div class="num">IV</div><h3>The Freeze</h3>
        <p>The model was frozen before the ledger opened. When it is wrong, the ledger says so in
        public. Nothing is re-tuned to make a chart look better — that is the whole point.</p>
        <svg width="120" height="10"><line x1="0" y1="5" x2="120" y2="5" stroke="#C6A962" stroke-opacity=".4"/><rect x="52" y="0" width="16" height="10" fill="none" stroke="#43A37C"/></svg>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="kicker">The Record</div>
    <h2>Latest <em>verdicts.</em></h2>
    <p class="lede">Graded entries, most recent first. Losses are printed in the same ink as wins —
    that is the arrangement.</p>
    <div style="margin-top:32px" data-reveal>{recent_html}</div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="kicker">The Evidence</div>
    <h2>September, <em>the holdout.</em></h2>
    <p class="lede">Before the ledger opened, the frozen policy was graded on September 2026 —
    a month it had never seen during any design step. This is its certificate.</p>
    <div class="cert" style="margin-top:40px" data-reveal>
      <div class="cert-top"><span>Assay certificate · 2026-09</span><span>Policy v8-jade-1.1 · frozen</span></div>
      <div class="stamp">Holdout verified</div>
      <div class="cert-body">
        <div class="cell"><b>{sc_hold['adj_roi']:+.1%}</b><span>Adjusted ROI</span></div>
        <div class="cell"><b>{sc_hold['roi']:+.1%}</b><span>Raw ROI</span></div>
        <div class="cell"><b>{sc_hold['n']}</b><span>Picks · 4.6/day</span></div>
        <div class="cell"><b>{sc_hold['wr']:.1%}</b><span>Win rate</span></div>
      </div>
    </div>
    <div data-reveal style="margin-top:56px">{eq_svg}
      <p class="lede" style="font-size:13px;margin-top:14px;font-family:var(--mono);letter-spacing:.12em;text-transform:uppercase;font-size:10.5px">
      Cumulative units · flat 1u — <span style="color:#3E8F6E">tuning Mar–Aug</span> · <span style="color:#C6A962">frozen holdout Sep</span></p></div>
    <div data-reveal style="margin-top:48px">{bars}</div>
    <table class="ledger-t" data-reveal style="margin-top:8px">
      <tr><th>Month</th><th>Picks</th><th>Adj ROI</th><th>Profit</th><th>Grade</th></tr>
      {month_cells}
    </table>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="kicker">The Referee</div>
    <h2>Pre-registered gates, <em>honest verdicts.</em></h2>
    <p class="lede">These bars were set in stone before September was ever scored. Two were missed.
    They are printed here anyway — the ledger exists to close them, not to hide them.</p>
    <table class="ledger-t" data-reveal style="margin-top:36px">
      <tr><th>Gate</th><th>Bar</th><th>September</th><th>Verdict</th></tr>
      <tr><td>Adjusted ROI</td><td class="mono">≥ +5%</td><td class="mono">+7.7%</td><td><span class="chip pass">Pass</span></td></tr>
      <tr><td>Months positive (tune)</td><td class="mono">≥ 75%</td><td class="mono">5 / 6</td><td><span class="chip pass">Pass</span></td></tr>
      <tr><td>Sample size</td><td class="mono">≥ 100 picks</td><td class="mono">95</td><td><span class="chip fail">Fail · n</span></td></tr>
      <tr><td>Significance</td><td class="mono">t ≥ 2.0</td><td class="mono">+1.22</td><td><span class="chip fail">Fail · t</span></td></tr>
      <tr><td>Concentration</td><td class="mono">top capper ≤ 40%</td><td class="mono">41%</td><td><span class="chip bline">Borderline</span></td></tr>
    </table>
    <div data-reveal style="margin-top:48px">
      <div class="kicker" style="margin-top:44px">What the model reads</div>
      {feats}
      <p class="lede" style="font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;margin-top:12px">
      Top features by contribution — who picks matters as much as the price</p>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="kicker">The Risk Page</div>
    <h2>What could <em>break it.</em></h2>
    <div class="risk" style="margin-top:30px">
      <p><b>One clean month.</b> September is a single holdout; its 90% confidence interval spans
      −4.5% to +19.7%. The forward ledger — 100 graded picks — is the real experiment.</p>
      <p><b>Prices at the whistle.</b> Backtest odds are recorded at grading time. If prices move
      between posting and grading, part of the measured edge may not be executable at bet time.</p>
      <p><b>Concentration.</b> 41% of September profit came from one capper. Cappers go cold; the
      daily cap and skill gate are the containment, not a cure.</p>
      <p><b>Drawdown.</b> Worst observed Sep drawdown: {dd:+.1f}u. Live variance will be worse.
      Stake sizes should assume a 15–20u drawdown is normal.</p>
      <p><b>Market drift.</b> The model is frozen between retrains. If the market adapts, the
      ledger decays in public view — by design, before stakes grow.</p>
      <p><b>This is not advice.</b> No picks are sold here. This is a public research experiment
      on disclosed data, staked at sizes that cannot hurt.</p>
    </div>
  </div>
</section>

<footer><div class="wrap" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:18px;width:100%">
  <span>Series VIII · Jade — cut from the same quarry as I–VII</span>
  <span>Built {pd.Timestamp.now():%Y-%m-%d %H:%M} · data through {fd['pick_date'].max().date()}</span>
  <span>Set in Fraunces &amp; Plex Mono</span>
</div></footer>

<script>
document.documentElement.classList.add('js');
function revealInView() {{
  document.querySelectorAll('[data-reveal]:not(.in), section:not(.in)').forEach(el => {{
    const r = el.getBoundingClientRect();
    if (r.top < window.innerHeight * 0.94) el.classList.add('in');
  }});
}}
const io = new IntersectionObserver((es) => {{
  es.forEach(e => {{ if (e.isIntersecting) {{ e.target.classList.add('in'); io.unobserve(e.target); }} }});
}}, {{ threshold: .12, rootMargin: '0px 0px -6% 0px' }});
document.querySelectorAll('[data-reveal],section').forEach(el => io.observe(el));
let _stk;
window.addEventListener('scroll', () => {{ clearTimeout(_stk); _stk = setTimeout(revealInView, 80); }}, {{ passive: true }});
revealInView();
const co = new IntersectionObserver((es) => {{
  es.forEach(e => {{
    if (!e.isIntersecting) return;
    const el = e.target, target = parseFloat(el.dataset.count), t0 = performance.now();
    const step = (t) => {{
      const p = Math.min((t - t0) / 1200, 1), v = Math.round(target * (1 - Math.pow(1 - p, 3)));
      el.textContent = v; if (p < 1) requestAnimationFrame(step);
    }};
    requestAnimationFrame(step); co.unobserve(el);
  }});
}}, {{ threshold: .6 }});
document.querySelectorAll('[data-count]').forEach(el => {{ el.textContent = '0'; co.observe(el); }});
</script>
</body></html>"""

    os.makedirs(OUT_DIR, exist_ok=True)
    out = args.out or os.path.join(OUT_DIR, "index.html")
    with open(out, "w") as fh:
        fh.write(html_doc)
    print(f"Site written: {out}")
    print(f"Ledger: {n_graded} graded / {n_pend} pending · profit {profit:+.1f}u · grade {grade}")

    if not args.mock:
        # Machine-readable summary for the Control Center selector page.
        # Written only on real runs, next to the published index.html.
        import json as _json
        summary_out = os.path.join(os.path.dirname(os.path.abspath(out)), "ledger_summary.json")
        with open(summary_out, "w") as fh:
            _json.dump({
                "series": "v8-jade",
                "updated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M %Z").strip(),
                "graded": int(n_graded),
                "pending": int(n_pend),
                "profit": round(float(profit), 2),
                "roi_adj": None if adj is None else round(float(adj) * 100, 2),
                "grade": grade,
                "policy_version": ledger.get("policy_version", ""),
                "start_date": ledger.get("start_date", ""),
            }, fh, indent=2)
        print(f"Summary JSON: {summary_out}")


if __name__ == "__main__":
    main()
