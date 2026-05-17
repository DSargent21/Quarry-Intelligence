import os
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import json
import warnings

warnings.filterwarnings('ignore')

try:
    from src.pipeline import SportsDataPipeline, FeatureEngineer
    from src.features.v5_dynamic_features import calculate_dynamic_features
except ImportError:
    from pipeline import SportsDataPipeline, FeatureEngineer
    from v5_dynamic_features import calculate_dynamic_features

class ConformalSniperV5:
    def __init__(self, target_win_rate=0.70):
        self.target_win_rate = target_win_rate
        # Incorporating the best features from v4 and the new dynamic v5 features
        self.base_features = [
            'acc_7d', 'roi_7d', 'vol_7d', 'acc_30d', 'roi_30d', 'vol_30d',
            'capper_experience', 'implied_prob', 'v4_consensus_count_lag1',
            'capper_roi_std_30d', 'capper_win_rate_30d', 'market_drift'
        ]
        self.dynamic_features = [
            'roi_volatility_ratio', 'consensus_roi_spread', 'roi_momentum'
        ]
        self.features = self.base_features + self.dynamic_features
        self.target = 'outcome'
        self.model = None
        self.conformal_threshold = 0.5  # Will be learned from calibration set

    def fetch_and_prepare(self):
        print("🔗 Fetching data (cached) and engineering v5 features...")
        pipeline = SportsDataPipeline()
        # Use cached data to prevent redundant network calls
        raw_df = pipeline.fetch_data_cached()
        if raw_df.empty:
            print("❌ No data fetched.")
            return pd.DataFrame()
            
        engineer = FeatureEngineer(raw_df)
        df = engineer.process()
        
        # Prepare for dynamic features
        # Rename columns to match v5_dynamic_features.py expectations
        df['capper'] = df['capper_id']
        df['capper_rolling_roi'] = df['roi_30d']
        df['volatility'] = df['vol_30d']
        df['market_consensus'] = df['implied_prob']
        if 'profit_units' in df.columns:
            df['return'] = df['profit_units']

        print("🧬 Computing v5 Dynamic Features...")
        df = calculate_dynamic_features(df)
        
        # Filter for training (binary outcomes only)
        df = df[df['outcome'].isin([0.0, 1.0])].copy()
        df['outcome'] = df['outcome'].astype(int)
        df = df.dropna(subset=self.features).sort_values('pick_date')
        
        return df

    def custom_asymmetric_loss(self, preds, dtrain):
        """
        Asymmetric loss: severely penalizes false positives (losing bets).
        This forces the model to be hyper-conservative.
        """
        labels = dtrain.get_label()
        preds = 1.0 / (1.0 + np.exp(-preds)) # sigmoid
        
        # We want to heavily penalize predicting 1 when label is 0 (False Positive)
        # penalty factor for FP
        fp_penalty = 5.0
        
        grad = preds - labels
        hess = preds * (1.0 - preds)
        
        # Apply penalty to gradient and hessian where label is 0
        grad = np.where(labels == 0, grad * fp_penalty, grad)
        hess = np.where(labels == 0, hess * fp_penalty, hess)
        
        return grad, hess

    def train_conformal_model(self, df):
        print(f"🚀 Training V5 Conformal Sniper on {len(df)} rows...")
        
        # Chronological Split: 70% Train, 15% Calibration, 15% Test
        n = len(df)
        train_idx = int(n * 0.7)
        cal_idx = int(n * 0.85)
        
        train_df = df.iloc[:train_idx]
        cal_df = df.iloc[train_idx:cal_idx]
        test_df = df.iloc[cal_idx:]
        
        X_train, y_train = train_df[self.features], train_df[self.target]
        X_cal, y_cal = cal_df[self.features], cal_df[self.target]
        X_test, y_test = test_df[self.features], test_df[self.target]
        
        print(f"📊 Split: Train={len(X_train)}, Cal={len(X_cal)}, Test={len(X_test)}")
        
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dcal = xgb.DMatrix(X_cal, label=y_cal)
        dtest = xgb.DMatrix(X_test, label=y_test)
        
        params = {
            'learning_rate': 0.05,
            'max_depth': 4,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'tree_method': 'hist',
            'random_state': 42,
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            # Hardware Acceleration: tree_method='hist' is highly efficient on Ryzen 7.
            # We keep it CPU-bound but multi-threaded for maximum stability on AMD.
            'n_jobs': -1 
        }
        
        # Train with Standard Logistic Loss
        print("🧠 Training XGBoost Engine...")
        evals = [(dtrain, 'train'), (dcal, 'cal')]
        self.model = xgb.train(
            params, dtrain, num_boost_round=200, 
            evals=evals, verbose_eval=False
        )
        
        # Conformal Prediction Calibration
        print("⚖️ Calibrating Conformal Prediction Interval...")
        # Get predictions on calibration set
        cal_probs = self.model.predict(dcal)
        
        # Find the threshold that guarantees the target win rate
        thresholds = np.linspace(0.01, 0.99, 100)
        best_threshold = 0.99
        
        for t in thresholds:
            selected = cal_probs >= t
            if np.sum(selected) > 0:
                win_rate = np.mean(y_cal[selected])
                if win_rate >= self.target_win_rate:
                    best_threshold = t
                    break
        
        self.conformal_threshold = best_threshold
        print(f"🎯 Conformal Threshold required for {self.target_win_rate*100}% win rate: {self.conformal_threshold:.4f}")
        
        # Evaluate on Test Set
        test_probs = self.model.predict(dtest)
        
        test_bets = test_probs >= self.conformal_threshold
        if np.sum(test_bets) > 0:
            test_win_rate = np.mean(y_test[test_bets])
            print(f"✅ Holdout Test Win Rate: {test_win_rate*100:.1f}% ({np.sum(y_test[test_bets])} / {np.sum(test_bets)} bets)")
        else:
            print("⚠️ Model is too conservative on test set; 0 bets placed.")
            
        return test_df.copy(), test_probs

    def backtest(self, test_df, test_probs):
        print("💰 Running V5 Financial Backtest with Kelly Staking...")
        test_df = test_df.copy()
        
        # Absolute Fix: ensure pick_date is a column
        if 'pick_date' not in test_df.columns:
            test_df = test_df.reset_index()
            
        test_df['predicted_prob'] = test_probs
        test_df['edge'] = test_df['predicted_prob'] - test_df['implied_prob']
        
        # FILTERS: Tightened for higher ROI while aiming for volume
        valid_bets = (test_df['predicted_prob'] >= self.conformal_threshold) & \
                     (test_df['edge'] >= 0.02) & \
                     (test_df['decimal_odds'] >= 1.70) & \
                     (test_df['decimal_odds'] <= 4.00)
                     
        cand = test_df[valid_bets].copy()
        
        if cand.empty:
            print("No bets passed the filters.")
            return
            
        # Dynamic Kelly Staking
        kelly_frac = 0.15
        cand['b'] = cand['decimal_odds'] - 1
        cand['kelly'] = ((cand['b'] * cand['predicted_prob']) - (1 - cand['predicted_prob'])) / cand['b']
        
        # Institutional Adjustment
        consensus_mult = np.where(cand['v4_consensus_count_lag1'] >= 3, 1.10, 1.0)
        cand['wager_unit'] = (cand['kelly'] * kelly_frac * 100 * consensus_mult).clip(0, 3.0)
        
        active_df = cand[cand['wager_unit'] > 0.01].copy()
        if active_df.empty:
            print("No bets passed the Kelly filters.")
            return
            
        # Daily Cap Loop (Robust)
        capped_list = []
        for date, group in active_df.groupby('pick_date'):
            risk = group['wager_unit'].sum()
            if risk > 10.0:
                group['wager_unit'] *= (10.0 / risk)
            capped_list.append(group)
        
        final_df = pd.concat(capped_list)
        
        # Calculate actual profit
        final_df['profit_actual'] = np.where(
            final_df['outcome'] == 1, 
            final_df['wager_unit'] * (final_df['decimal_odds'] - 1), 
            -final_df['wager_unit']
        )
        
        # Stats
        daily_counts = final_df.groupby('pick_date').size()
        avg_bets_per_day = daily_counts.mean()
        
        total_profit = final_df['profit_actual'].sum()
        total_risk = final_df['wager_unit'].sum()
        roi = (total_profit / total_risk) * 100 if total_risk > 0 else 0
        win_rate = final_df['outcome'].mean() * 100
        
        start_date = final_df['pick_date'].min().date()
        end_date = final_df['pick_date'].max().date()

        print(f"\n=====================================")
        print(f"💎 V5 CONFORMAL SNIPER RESULTS")
        print(f"=====================================")
        print(f"Date Range:        {start_date} to {end_date}")
        print(f"Total Bets:        {len(final_df)}")
        print(f"Avg Bets / Day:    {avg_bets_per_day:.2f}")
        print(f"Win Rate:          {win_rate:.1f}%")
        print(f"Net Profit:        {total_profit:+.2f} Units")
        print(f"ROI:               {roi:+.1f}%")
        print(f"=====================================\n")

    def save_model(self, path='models/v5_conformal_sniper.json'):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # XGBoost handles custom objectives best when saved to json or native binary format.
        self.model.save_model(path)
        print(f"📁 Model Engine saved to {path}")
        
        # Save config and threshold
        with open('models/v5_config.json', 'w') as f:
            json.dump({
                "features": self.features,
                "conformal_threshold": self.conformal_threshold,
                "target_win_rate": self.target_win_rate,
                "Min_Odds": 1.70,
                "Daily_Cap": 10.0
            }, f, indent=4)
        print("📁 V5 Configuration saved.")

if __name__ == "__main__":
    v5 = ConformalSniperV5(target_win_rate=0.58)
    df = v5.fetch_and_prepare()
    if not df.empty:
        test_df, test_probs = v5.train_conformal_model(df)
        v5.backtest(test_df, test_probs)
        v5.save_model()
