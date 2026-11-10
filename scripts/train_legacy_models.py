"""Re-export the v1 Pyrite / v2 Diamond / v3 Obsidian scorecards.

The shipped pickles in `models/` are corrupt (UnpicklingError), so every daily
run silently fell back to heuristic signatures. This script retrains each
series on rows that predate its release date only, so its forward track stays
out-of-sample, and writes fresh joblib artifacts the loader can read.

Usage:  python3 scripts/train_legacy_models.py [--out models]
"""
import argparse
import os
import sys

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from pipeline import SportsDataPipeline, FeatureEngineer  # noqa: E402

FEATURES = [
    'acc_7d', 'roi_7d', 'vol_7d', 'acc_30d', 'roi_30d', 'vol_30d',
    'roll_sharpe_30d', 'capper_win_rate_30d', 'v4_consensus_count_lag1',
    'capper_experience', 'implied_prob', 'decimal_odds', 'is_momentum_sport',
]

# Model file -> (training cutoff = day before that series started tracking)
SERIES = {
    'v1_pyrite.pkl': '2025-11-20',
    'v2_diamond.pkl': '2025-11-29',
    'v3_obsidian.pkl': '2025-12-26',
}


def build_training_frame():
    raw = SportsDataPipeline().fetch_data_cached()
    raw['pick_date'] = pd.to_datetime(raw['pick_date'])
    df = FeatureEngineer(raw).process()
    df = df[df['outcome'].isin([0.0, 1.0])].copy()
    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        raise SystemExit(f'missing features: {missing}')
    df[FEATURES] = df[FEATURES].apply(pd.to_numeric, errors='coerce').astype('float32')
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(BASE_DIR, 'models'))
    args = ap.parse_args()

    df = build_training_frame()
    print(f'training frame: {len(df)} settled picks, all dates')

    for filename, cutoff in SERIES.items():
        cutoff_ts = pd.Timestamp(cutoff)
        train = df[df['pick_date'] <= cutoff_ts]
        if len(train) < 2000:
            raise SystemExit(f'{filename}: only {len(train)} training rows before {cutoff}')
        X, y = train[FEATURES].fillna(0.0), train['outcome'].astype(int)

        model = XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.85, colsample_bytree=0.85, min_child_weight=5,
            reg_lambda=1.0, eval_metric='logloss', n_jobs=1, random_state=42,
        )
        model.fit(X, y)

        # In-sample sanity only; forward track starts the day after the cutoff.
        p = model.predict_proba(X)[:, 1]
        acc = float(((p >= 0.5) == y.to_numpy()).mean())
        later = df[df['pick_date'] > cutoff_ts]
        out = f'{filename}: rows={len(train)} acc={acc:.3f}'
        if len(later):
            pl = model.predict_proba(later[FEATURES].fillna(0.0))[:, 1]
            out += f' | post-cutoff rows={len(later)} mean_prob={pl.mean():.3f}'
        print(out)

        path = os.path.join(args.out, filename)
        joblib.dump(model, path, compress=3)
        loaded = joblib.load(path)
        print(f'  wrote {path} ({os.path.getsize(path)//1024} KB), reload ok, '
              f'features={len(getattr(loaded, "feature_names_in_", []))}')


if __name__ == '__main__':
    main()
