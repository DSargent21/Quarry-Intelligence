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
    from src.features.v5_dynamic_features import calculate_dynamic_features
except ImportError:
    from pipeline import SportsDataPipeline, FeatureEngineer
    from v5_dynamic_features import calculate_dynamic_features
    from v5_dynamic_features import calculate_dynamic_features

class MasterSniperCarnelian:
    def __init__(self, min_win_rate=0.57): 
        self.min_win_rate = min_win_rate
        self.features = [
            'acc_7d', 'roi_7d', 'vol_7d', 'acc_30d', 'roi_30d', 'vol_30d',
            'capper_experience', 'implied_prob', 'v4_consensus_count_lag1',
            'market_drift', 'roi_volatility_ratio', 'consensus_roi_spread', 
            'roi_momentum', 'bets_last_24h', 'synergy_score', 'is_dna_pattern'
        ]
        self.target = 'outcome'
        self.model = None
        self.conformal_threshold = 0.5
        self.best_bayesian_roi = -1.0

    def fetch_and_prepare(self):
        print(f"🔗 [CARNELIAN] Fetching and preparing base features (Target Win% >= {self.min_win_rate:.0%})...")
        pipeline = SportsDataPipeline()
        raw_df = pipeline.fetch_data_cached()
        if raw_df.empty:
            return pd.DataFrame()
            
        engineer = FeatureEngineer(raw_df)
        df = engineer.process()
        
        df['capper'] = df['capper_id']
        df['capper_rolling_roi'] = df['roi_30d']
        df['volatility'] = df['vol_30d']
        df['market_consensus'] = df['implied_prob']
        
        if 'profit_units' not in df.columns:
            if 'decimal_odds' in df.columns:
                df['profit_units'] = np.where(df['outcome'] == 1, df['decimal_odds'] - 1, -1)
            else:
                df['profit_units'] = np.where(df['outcome'] == 1, 0.9, -1)
        
        df['return'] = df['profit_units']

        print("🧬 [CARNELIAN] Computing Dynamic V5 Features (Lagged)...")
        df = calculate_dynamic_features(df)
        
        # Chronological Split BEFORE Synergy calculation to avoid leakage
        df = df[df['outcome'].isin([0.0, 1.0])].copy()
        df['outcome'] = df['outcome'].astype(int)
        df = df.dropna(subset=['roi_30d', 'vol_30d', 'implied_prob']).sort_values('pick_date')
        
        n_rows = len(df)
        train_idx = int(n_rows * 0.75)
        train_df_raw = df.iloc[:train_idx]
        
        print("🧠 [CARNELIAN] Calculating Synergy Map on Training Data only...")
        train_df_raw['prev_league'] = train_df_raw.groupby('capper_id')['league_name'].shift(1)
        train_df_raw['prev_outcome'] = train_df_raw.groupby('capper_id')['outcome'].shift(1)
        syn_stats = train_df_raw[train_df_raw['prev_outcome'] == 1].groupby(['prev_league', 'league_name'])['outcome'].mean()
        synergy_map = syn_stats[syn_stats > 0.52].to_dict()
        
        print(f"✅ Found {len(synergy_map)} significant synergies in training data.")

        print("🚀 [CARNELIAN] Computing Zenith Features with Training Synergy Map...")
        df = calculate_dynamic_features(df, synergy_map=synergy_map)
        
        df = df.dropna(subset=self.features).sort_values('pick_date')
        return df

    def calculate_bayesian_roi(self, n, total_profit):
        if n == 0:
            return -0.05
        return (total_profit - 1.5) / (n + 30)

    def simulate_staking(self, df, sequence=[0.3, 0.66, 1.45, 3.19, 5.0]):
        """
        Simulates the Zenith Optimized Hybrid Recovery Sequence.
        Returns total profit and total units staked.
        """
        seq_idx = 0
        max_idx = len(sequence) - 1
        total_profit = 0
        total_staked = 0
        
        # Sort by date for chronological simulation
        df = df.sort_values('pick_date')
        
        for _, row in df.iterrows():
            bet = sequence[seq_idx]
            total_staked += bet
            if row[self.target] == 1:
                total_profit += bet * (row['decimal_odds'] - 1)
                seq_idx = 0 # Reset on win
            else:
                total_profit -= bet
                seq_idx = (seq_idx + 1) if seq_idx < max_idx else 0 # Step up or reset on cap
                
        return total_profit, total_staked

    def train(self, df):
        print(f"🚀 [CARNELIAN] Training on {len(df)} rows using Ryzen 7700 (16 threads)...")
        
        n_rows = len(df)
        train_idx = int(n_rows * 0.75)
        cal_idx = int(n_rows * 0.90)
        
        train_df = df.iloc[:train_idx]
        cal_df = df.iloc[train_idx:cal_idx]
        test_df = df.iloc[cal_idx:]
        
        X_train, y_train = train_df[self.features], train_df[self.target]
        X_cal, y_cal = cal_df[self.features], cal_df[self.target]
        X_test, y_test = test_df[self.features], test_df[self.target]
        
        profit_cal = cal_df['return']
        
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dcal = xgb.DMatrix(X_cal, label=y_cal)
        
        # Optimized for Ryzen 7700
        params = {
            'max_depth': 6,
            'eta': 0.01,
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            'subsample': 0.7,
            'colsample_bytree': 0.7,
            'tree_method': 'hist',
            'nthread': 16
        }
        
        print("🧠 Training XGBoost with Early Stopping...")
        self.model = xgb.train(
            params, 
            dtrain, 
            num_boost_round=3000,
            evals=[(dtrain, 'train'), (dcal, 'eval')],
            early_stopping_rounds=100,
            verbose_eval=False
        )
        
        print(f"✅ Training complete. Best iteration: {self.model.best_iteration}")
        
        print(f"⚖️ [CARNELIAN] Calibrating for Max Marketability (Target WR >= {self.min_win_rate:.0%})...")
        cal_probs = self.model.predict(xgb.DMatrix(X_cal))
        
        potential_thresholds = np.linspace(0.5, 0.95, 91)
        best_threshold = 0.5
        best_score = -999
        found_valid = False
        
        # We need odds for the average odds constraint and dates for picks/day
        odds_cal = cal_df['decimal_odds'] if 'decimal_odds' in cal_df.columns else (1 / cal_df['implied_prob'])
        
        cal_df['pick_date'] = pd.to_datetime(cal_df['pick_date'])
        n_days = (cal_df['pick_date'].max() - cal_df['pick_date'].min()).days
        if n_days <= 0: n_days = 1

        for t in potential_thresholds:
            mask = cal_probs >= t
            n_signals = mask.sum()
            
            if n_signals >= 10:
                win_rate = y_cal[mask].mean()
                total_profit = profit_cal[mask].sum()
                avg_odds = odds_cal[mask].mean()
                picks_per_day = n_signals / n_days
                
                # Marketable Constraints
                if win_rate >= self.min_win_rate and total_profit > 0 and avg_odds >= 1.62 and picks_per_day >= 7:
                    score = win_rate
                    if score > best_score:
                        best_score = score
                        best_threshold = t
                        found_valid = True
                        print(f"   [VALID] t={t:.3f} | WR={win_rate:.2%} | Picks/Day={picks_per_day:.1f} | Profit={total_profit:.1f}")
                        
        if not found_valid:
            print(f"   ⚠️ Could not satisfy marketable constraints. Reverting to safe maximum.")
            best_threshold = 0.90
            
        self.conformal_threshold = best_threshold
        self.best_bayesian_roi = best_score
        
        print(f"✅ [CARNELIAN] Optimal Threshold: {self.conformal_threshold:.4f}")
        
        # Test Evaluation
        test_probs = self.model.predict(xgb.DMatrix(X_test))
        signals_mask = test_probs >= self.conformal_threshold
        
        # TEST EVALUATION (Based on Zenith Audit Findings)
        # Decision: Default to 1.0u Flat Staking for Institutional Consistency
        
        final_wr = y_test[signals_mask].mean()
        final_n = signals_mask.sum()
        
        # 1. Flat Staking (Production Standard)
        final_profit = test_df.loc[signals_mask, 'return'].sum() 
        final_staked = final_n * 1.0
        
        # 2. Hybrid Staking (Safety Reference)
        hybrid_profit, hybrid_staked = self.simulate_staking(test_df[signals_mask])
        
        final_roi = (final_profit / final_staked) * 100 if final_staked > 0 else 0
        final_adj_roi = self.calculate_bayesian_roi(final_n, final_profit)
        
        # Picks per day calculation for test set
        test_df['pick_date'] = pd.to_datetime(test_df['pick_date'])
        test_days = (test_df['pick_date'].max() - test_df['pick_date'].min()).days
        if test_days <= 0: test_days = 1
        picks_per_day = final_n / test_days

        print(f"📊 [CARNELIAN] Test Results (PRODUCTION STANDARD: 1.0u FLAT):")
        print(f"   - Signal Count: {final_n} ({picks_per_day:.2f} picks/day)")
        print(f"   - Win Rate: {final_wr:.2%}")
        print(f"   - Total Profit: {final_profit:+.2f} Units")
        print(f"   - Real ROI: {final_roi:.2f}% (on {final_staked:.1f}u staked)")
        print(f"   - Adjusted ROI (Grade): {final_adj_roi:.2%}")
        print(f"   - [Ref] Hybrid Staking Net: {hybrid_profit:+.2f}u (on {hybrid_staked:.1f}u staked)")
        
        return {
            'win_rate': final_wr,
            'signals': final_n,
            'roi': final_roi,
            'threshold': self.conformal_threshold
        }

    def save(self, model_path='models/Carnelian_marketable_sniper.json'):
        os.makedirs('models', exist_ok=True)
        self.model.save_model(model_path)
        config = {
            'features': self.features,
            'threshold': self.conformal_threshold,
            'min_win_rate': self.min_win_rate,
            'model_type': 'Carnelian_Rainmaker'
        }
        with open(model_path.replace('.json', '_config.json'), 'w') as f:
            json.dump(config, f)
        print(f"💾 [CARNELIAN] Model saved to {model_path}")

if __name__ == "__main__":
    sniper = MasterSniperCarnelian()
    df = sniper.fetch_and_prepare()
    if not df.empty:
        results = sniper.train(df)
        sniper.save()
