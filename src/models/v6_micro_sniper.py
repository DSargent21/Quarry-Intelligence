import os
import pandas as pd
import numpy as np
import joblib
import json
import xgboost as xgb
from src.pipeline import SportsDataPipeline, FeatureEngineer

class MicroSniperV6:
    def __init__(self):
        # V6: Focus on fast momentum and synergy
        self.features = [
            'roi_1d', 'roi_3d', 'roi_7d',
            'acc_1d', 'acc_3d', 'acc_7d',
            'bets_last_24h', 'is_synergy_pick',
            'implied_prob', 'is_momentum_sport',
            'capper_experience', 'days_since_prev'
        ]
        self.target = 'outcome'
        self.model = None

    def engineer_v6(self, df):
        print("🧬 Engineering V6 Micro-Features...")
        # Sort for temporal integrity
        df = df.sort_values(['capper_id', 'pick_date'])
        
        # 1. Fast Windows
        # To use time-based rolling in groupby, we need pick_date as index
        df = df.set_index('pick_date', drop=False)
        g = df.groupby('capper_id')
        
        for d in [1, 3, 7]:
            # Shift(1) to avoid data leakage (only use past results)
            df[f'roi_{d}d'] = g['profit_units'].transform(lambda x: x.shift(1).rolling(window=f'{d}D').sum()).fillna(0)
            df[f'acc_{d}d'] = g['outcome'].transform(lambda x: x.shift(1).rolling(window=f'{d}D').mean()).fillna(0.5)

        # 2. Volume Toxicity (24h count)
        df['bets_last_24h'] = g['pick_date'].transform(lambda x: x.rolling('24h', closed='left').count()).fillna(0)
        
        # 3. Synergy Node
        # Does this capper have a high ROI in a DIFFERENT sport?
        # Simplify: Just use 7d ROI and 30d ROI diff
        df['is_synergy_pick'] = ((df['roi_7d'] > 0) & (df['roi_30d'] < df['roi_7d'])).astype(int)

        # 4. Clean for training
        df = df[df['outcome'].isin([0, 1])].copy()
        df = df.dropna(subset=self.features)
        df = df.reset_index(drop=True)
        return df

    def train(self, df):
        print(f"🚀 Training V6 Micro-Sniper with TimeSeriesSplit on {len(df)} samples...")
        from sklearn.model_selection import TimeSeriesSplit
        
        X = df[self.features]
        y = df[self.target]
        
        tscv = TimeSeriesSplit(n_splits=5)
        fold = 1
        cv_scores = []
        
        for train_index, test_index in tscv.split(X):
            X_train, X_test = X.iloc[train_index], X.iloc[test_index]
            y_train, y_test = y.iloc[train_index], y.iloc[test_index]
            
            fold_model = xgb.XGBClassifier(
                n_estimators=1000,
                learning_rate=0.01, # Slower learning to prevent memorization
                max_depth=4,
                subsample=0.7,
                colsample_bytree=0.7,
                monotone_constraints="(1, 1, 1, 1, 1, 1, -1, 1, 0, 1, 0, 0)",
                random_state=42,
                n_jobs=-1,
                early_stopping_rounds=50 # Move to constructor
            )
            
            fold_model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                verbose=False
            )
            
            # Score fold on a "Profitability" metric, not just accuracy
            preds = fold_model.predict_proba(X_test)[:, 1]
            test_df = df.iloc[test_index].copy()
            test_df['prob'] = preds
            test_df['edge'] = test_df['prob'] - test_df['implied_prob']
            
            # Simulate surgical picks for this fold
            picks = test_df[(test_df['edge'] > 0.02) & (test_df['bets_last_24h'] <= 5)]
            if not picks.empty:
                wr = picks['outcome'].mean()
                roi = (picks['profit_units'].sum() / picks['unit'].sum())
                cv_scores.append(roi)
                print(f"  📂 Fold {fold}: WR: {wr:.1%} | ROI: {roi:+.1%} | Picks: {len(picks)}")
            else:
                print(f"  📂 Fold {fold}: No picks identified.")
                cv_scores.append(0)
            
            fold += 1
            
        print(f"🏆 Mean CV ROI: {np.mean(cv_scores):+.1%}")

        # Final Train on All Data (excluding the very last buffer to preserve 'unknown' future)
        final_model = xgb.XGBClassifier(
            n_estimators=300, # Use moderate estimators found in CV
            learning_rate=0.01,
            max_depth=4,
            subsample=0.7,
            colsample_bytree=0.7,
            monotone_constraints="(1, 1, 1, 1, 1, 1, -1, 1, 0, 1, 0, 0)",
            random_state=42,
            n_jobs=-1
        )
        final_model.fit(X, y)
        self.model = final_model

    def save(self):
        os.makedirs('models', exist_ok=True)
        joblib.dump(self.model, 'models/v6_micro_sniper.pkl')
        with open('models/v6_config.json', 'w') as f:
            json.dump({
                "features": self.features,
                "Min_Edge": 0.02,
                "Max_Daily_Bets": 5,
                "Monotone": True
            }, f, indent=4)
        print("📁 V6 saved.")

if __name__ == "__main__":
    pipeline = SportsDataPipeline()
    raw = pipeline.fetch_data_cached()
    engineer = FeatureEngineer(raw)
    df = engineer.process()
    
    v6 = MicroSniperV6()
    data = v6.engineer_v6(df)
    v6.train(data)
    v6.save()
