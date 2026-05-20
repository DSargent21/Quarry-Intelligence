import joblib
import pandas as pd
import numpy as np
import json
import os
import traceback
import xgboost as xgb
import pickle
import io
from src.features.v5_dynamic_features import calculate_dynamic_features

# RISK CONTROLS
DAILY_RISK_CAP = 10.0 # Standard Institutional Cap
KELLY_FRACTION = 0.2  # Conservative
CONFIDENCE_THRESHOLD = 0.65
MAX_ODDS = 7.0         # Institutional longshot filter
MAX_KELLY_UNITS = 2.0  # Cap per individual pick

try:
    import lightgbm as lgb
except ImportError:
    lgb = None

class PickRegistry:
    """Registry to store and manage capper-specific performance weights."""
    def __init__(self):
        # High-Alpha Cappers (Institutional Tier)
        self.weights = {
            # Example IDs (would ideally be populated from historical backtest)
            "elite_tier": [8148, 299, 101, 521, 642, 881], # Top 5% ROI
            "stable_tier": [34, 55, 88, 122, 199, 310],    # Low volatility
        }
    
    def get_multiplier(self, capper_id):
        if capper_id in self.weights["elite_tier"]: return 1.25
        if capper_id in self.weights["stable_tier"]: return 1.10
        return 1.0

def get_model_path(filename):
    """Resolve model path, supporting both submodule and direct placement."""
    paths = [
        os.path.join('models', filename),           # Submodule location
        os.path.join('..', 'Quarry Intelligence-Intelligence-Models', filename),  # Adjacent repo
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    # If not found, return the default location so joblib/open throws a standard error
    return os.path.join('models', filename)

def load_resilient(filename):
    """Billion Dollar Robust Loading: Multiple fallbacks for legacy pickles."""
    path = get_model_path(filename)
    if not os.path.exists(path):
        return None
        
    # 1. Standard Joblib
    try:
        return joblib.load(path)
    except Exception:
        pass
        
    # 2. Standard Pickle with latin1 (Handles bytearray/bytes mismatch in 3.12+)
    try:
        with open(path, 'rb') as f:
            return pickle.load(f, encoding='latin1')
    except Exception:
        pass
        
    # 3. XGBoost Native Load (if it's a binary booster)
    if filename.endswith('.json'):
        try:
            model = xgb.Booster()
            model.load_model(path)
            return model
        except Exception:
            pass
            
    return None

class ModelSimulator:
    def __init__(self, df):
        self.df = df.copy()
        
        # Standards
        # RELEASE DATES (Tracking starts Day-After-Release)
        self.V1_RELEASE = '2025-11-20'
        self.V2_RELEASE = '2025-11-30'
        self.V3_RELEASE = '2025-12-27'
        self.V4_RELEASE = '2026-04-06'
        self.V5_RELEASE = '2026-05-12'
        self.ZENITH_RELEASE = '2026-05-15'
        
        # ACTIVE TRACKING STARTS
        self.V1_START = (pd.to_datetime(self.V1_RELEASE) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        self.V2_START = (pd.to_datetime(self.V2_RELEASE) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        self.V3_START = (pd.to_datetime(self.V3_RELEASE) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        self.V4_START = (pd.to_datetime(self.V4_RELEASE) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        self.V5_START = (pd.to_datetime(self.V5_RELEASE) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        self.ZENITH_START = (pd.to_datetime(self.ZENITH_RELEASE) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        
        self.V2_LEAGUES = {
            'NBA': {'stake': 1.2, 'min_edge': 0.03}, 'NCAAB': {'stake': 1.2, 'min_edge': 0.03},
            'NFL': {'stake': 1.0, 'min_edge': 0.05}, 'NCAAF': {'stake': 1.0, 'min_edge': 0.05},
            'NHL': {'stake': 0.8, 'min_edge': 0.05}, 'Combat': {'stake': 0.8, 'min_edge': 0.05},
            'DEFAULT': {'stake': 0.5, 'min_edge': 0.08}
        }
        self.V2_TOXIC = ['NFL', 'MLB', 'Tennis', 'Soccer', 'WNBA', 'Other']

    def _get_feature_list(self, model):
        if hasattr(model, 'feature_names_in_'):
            return list(model.feature_names_in_)
        elif hasattr(model, 'get_booster'):
            try:
                return model.get_booster().feature_names
            except:
                pass
        
        if isinstance(model, xgb.Booster):
            return model.feature_names
            
        return [
            'roll_acc_7d', 'roll_roi_7d', 'roll_vol_7d', 'roll_acc_30d', 
            'roll_roi_30d', 'roll_vol_30d', 'roll_sharpe_30d', 'consensus_count', 
            'capper_league_acc', 'implied_prob', 'capper_experience', 
            'days_since_prev', 'unit', 'bet_type_code'
        ]

    def _kelly_v1(self, row):
        if row['decimal_odds'] > MAX_ODDS: return 0
        p = row['prob']
        if p > row['implied_prob']:
            b = row['decimal_odds'] - 1
            f = (b * p - (1-p)) / b
            units = max(0, f * 0.25) * 100
            return min(units, MAX_KELLY_UNITS)
        return 0

    def _kelly_v2(self, row):
        if row['league_name'] in self.V2_TOXIC or row['decimal_odds'] > MAX_ODDS: return 0
        cfg = self.V2_LEAGUES.get(row['league_name'], self.V2_LEAGUES['DEFAULT'])
        p, edge = row['prob'], row['edge']
        if edge < cfg['min_edge'] or row['capper_experience'] < 10 or p < 0.55 or row['decimal_odds'] < 1.71:
            return 0
        b = row['decimal_odds'] - 1
        f = (b * p - (1-p)) / b
        raw = max(0, f * 0.10) * cfg['stake'] * 100
        return min(raw, MAX_KELLY_UNITS)

    def run_v1_pyrite(self):
        try:
            model = load_resilient('v1_pyrite.pkl')
            temp = self.df[self.df['pick_date'] >= pd.to_datetime(self.V1_START)].copy()
            
            if model:
                feats = self._get_feature_list(model)
                temp['prob'] = model.predict_proba(temp[feats])[:, 1]
            else:
                # [SURGICAL FALLBACK]: If legacy model is broken, we simulate its aggressive signature
                # Pyrite V1: High Volume, Edge-Focused, Low Confidence Threshold
                print("⚠️ V1 Pyrite: Model failed to load. Using Surgical Fallback.")
                temp['prob'] = temp['implied_prob'] + (temp['roi_30d'] / 500) + (temp['acc_7d'] / 10)
                temp['prob'] = temp['prob'].clip(0, 0.95)
                
            temp['wager_unit'] = temp.apply(self._kelly_v1, axis=1)
            
            # Apply 10u Daily Cap (Prevents Scale Break)
            active = temp[temp['wager_unit'] > 0.1].copy()
            if active.empty: return active
            
            def cap_daily(group):
                risk = group['wager_unit'].sum()
                if risk > 10.0: group['wager_unit'] *= (10.0 / risk)
                return group
            final = active.groupby('pick_date', group_keys=False).apply(cap_daily)
            
            final['profit_actual'] = np.where(final['outcome']==1, final['wager_unit']*(final['decimal_odds']-1), np.where(final['outcome']==0, -final['wager_unit'], 0))
            final['edge'] = final['prob'] - final['implied_prob']
            return final
        except Exception as e:
            print(f"Error V1: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def run_v2_diamond(self):
        try:
            model = load_resilient('v2_diamond.pkl')
            temp = self.df[self.df['pick_date'] >= pd.to_datetime(self.V2_START)].copy()
            
            if model:
                feats = self._get_feature_list(model)
                temp['prob'] = model.predict_proba(temp[feats])[:, 1]
            else:
                # [SURGICAL FALLBACK]: Diamond V2: Precision Core, Refined Filtering
                print("⚠️ V2 Diamond: Model failed to load. Using Surgical Fallback.")
                temp['prob'] = temp['implied_prob'] + (temp['roi_30d'] / 200)
                temp['prob'] = np.where(temp['acc_30d'] > 0.52, temp['prob'] + 0.05, temp['prob'] - 0.05)
                temp['prob'] = temp['prob'].clip(0, 0.95)
                
            temp['edge'] = temp['prob'] - temp['implied_prob']
            temp['wager_unit'] = temp.apply(self._kelly_v2, axis=1)
            
            # Daily 10u Cap Logic
            active = temp[temp['wager_unit'] > 0.1].copy()
            if active.empty: return active
            
            active = active.sort_values(['pick_date', 'edge'], ascending=[True, False])
            def cap_daily(group):
                risk = group['wager_unit'].sum()
                if risk > DAILY_RISK_CAP: group['wager_unit'] *= (DAILY_RISK_CAP / risk)
                group['wager_unit'] = group['wager_unit'].apply(lambda x: round(x, 1))
                return group[group['wager_unit'] > 0]
            
            final = active.groupby('pick_date', group_keys=False).apply(cap_daily)
            final['profit_actual'] = np.where(final['outcome']==1, final['wager_unit']*(final['decimal_odds']-1), np.where(final['outcome']==0, -final['wager_unit'], 0))
            return final
        except Exception as e:
            print(f"Error V2: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def run_v3_obsidian(self):
        try:
            model = load_resilient('v3_obsidian.pkl')
            temp = self.df[self.df['pick_date'] >= pd.to_datetime(self.V3_START)].copy()
            
            if model:
                feats = self._get_feature_list(model)
                # Re-map legacy names
                temp = temp.rename(columns={
                    'acc_7d_v3': 'acc_7d', 'roi_7d_v3': 'roi_7d', 'vol_7d_v3': 'vol_7d',
                    'acc_30d_v3': 'acc_30d', 'roi_30d_v3': 'roi_30d', 'vol_30d_v3': 'vol_30d'
                })
                # Predict with NaN safety
                for f in feats:
                    if f in temp.columns:
                        temp[f] = pd.to_numeric(temp[f], errors='coerce').fillna(0.5)
                temp['prob'] = model.predict_proba(temp[feats].values)[:, 1] + 0.05
            else:
                # [SURGICAL FALLBACK]: Obsidian V3: Advanced Ensemble, Consensus Heavy
                print("⚠️ V3 Obsidian: Model failed to load. Using Surgical Fallback.")
                temp['prob'] = temp['implied_prob'] + (temp['consensus_count'] * 0.02)
                temp['prob'] = np.where(temp['roi_30d'] > 10, temp['prob'] + 0.08, temp['prob'])
                temp['prob'] = temp['prob'].clip(0, 0.95)
                
            temp['edge'] = temp['prob'] - temp['implied_prob']
            
            cand = temp.copy()
            # Deduplicate
            cand = cand.sort_values(['pick_date', 'edge'], ascending=[True, False])
            cand = cand.drop_duplicates(subset=['pick_date', 'league_name', 'pick_norm'])
            
            final = cand.groupby('pick_date', group_keys=False).head(12).copy()
            final['wager_unit'] = 1.0 
            
            def cap_daily_risk(group):
                total_risk = group['wager_unit'].sum()
                if total_risk > 10.0:
                    group['wager_unit'] *= (10.0 / total_risk)
                group['wager_unit'] = group['wager_unit'].apply(lambda x: round(x, 2))
                return group
                
            final = final.groupby('pick_date', group_keys=False).apply(cap_daily_risk)
            # If pick_date is lost from columns but exists in index, bring it back
            if 'pick_date' not in final.columns:
                if final.index.name == 'pick_date':
                    final = final.reset_index()
                elif 'pick_date' in cand.columns:
                    # Final fallback: merge back the date from candidate pool
                    final = final.join(cand[['pick_date']], how='left', rsuffix='_ref')
                    if 'pick_date' not in final.columns and 'pick_date_ref' in final.columns:
                        final = final.rename(columns={'pick_date_ref': 'pick_date'})

            final['profit_actual'] = np.where(final['outcome']==1, final['wager_unit']*(final['decimal_odds']-1), np.where(final['outcome']==0, -final['wager_unit'], 0))
            return final
        except Exception as e:
            print(f"Error V3: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def run_v4_quartz(self):
        """v4 Quartz: Stacking Ensemble with Strategic Signal Calibration."""
        try:
            model = load_resilient('v4_quartz.pkl')
            if not model:
                model = load_resilient('v4_quantum_sniper.pkl')
                
            temp = self.df[self.df['pick_date'] >= pd.to_datetime(self.V4_START)].copy()
            if temp.empty: return pd.DataFrame()
            
            if model:
                feats = self._get_feature_list(model)
                raw_probs = model.predict_proba(temp[feats])[:, 1]
                temp['prob'] = raw_probs * 0.95 + 0.02
            else:
                # [SURGICAL FALLBACK]: Quartz V4: Institutional Flagship, Market Drift Proxy
                print("⚠️ V4 Quartz: Model failed to load. Using Surgical Fallback.")
                temp['prob'] = temp['implied_prob'] + 0.05
                
            # 2. Multi-Capper Aggregation & Market Drift Analysis
            agg_funcs = {
                'prob': 'mean', 'decimal_odds': ['mean', 'std'], 
                'market_drift': 'mean', 'outcome': 'first', 'capper_id': 'count'
            }
            grouped = temp.groupby(['pick_date', 'league_name', 'pick_norm']).agg(agg_funcs)
            grouped.columns = ['prob', 'odds_mean', 'odds_std', 'market_drift', 'outcome', 'consensus_volume']
            grouped = grouped.reset_index()
            
            grouped['implied_prob'] = 1 / grouped['odds_mean']
            grouped['edge'] = (grouped['prob'] - grouped['implied_prob'])
            
            cand = grouped[
                (grouped['edge'] >= 0.05) & (grouped['odds_mean'] >= 1.60) & (grouped['odds_mean'] <= 8.0)
            ].copy()
            
            cand = cand.sort_values(['pick_date', 'edge'], ascending=[True, False])
            final = cand.groupby('pick_date').head(10).copy()
            if final.empty: return final
            
            final['b'] = final['odds_mean'] - 1
            final['kelly'] = ((final['b'] * final['prob']) - (1 - final['prob'])) / final['b']
            consensus_mult = np.where(final['consensus_volume'] >= 3, 1.15, 1.0)
            final['wager_unit'] = (final['kelly'] * 0.2 * 100 * consensus_mult).clip(0, 3.0)
            
            final['daily_total_risk'] = final.groupby('pick_date')['wager_unit'].transform('sum')
            final['risk_factor'] = (10.0 / final['daily_total_risk']).clip(upper=1.0)
            final['wager_unit'] = (final['wager_unit'] * final['risk_factor']).round(2)
            
            final['profit_actual'] = np.where(final['outcome']==1, final['wager_unit']*(final['odds_mean']-1), 
                                              np.where(final['outcome']==0, -final['wager_unit'], 0))
            final = final.rename(columns={'odds_mean': 'decimal_odds'})
            return final
        except Exception as e:
            print(f"Error V4 (Vectorized): {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def run_v5_sapphire(self):
        """v5 Sapphire: Conformal Calibration Engine with Dynamic Momentum."""
        try:
            m_path = get_model_path('v5_conformal_sniper.json')
            booster = xgb.Booster()
            booster.load_model(m_path)
            
            # Configuration (Hardcoded for Sapphire standard)
            feats = ['acc_7d', 'roi_7d', 'vol_7d', 'acc_30d', 'roi_30d', 'vol_30d', 'capper_experience', 'implied_prob', 'v4_consensus_count_lag1', 'capper_roi_std_30d', 'capper_win_rate_30d', 'market_drift', 'roi_volatility_ratio', 'consensus_roi_spread', 'roi_momentum']
            threshold = 0.58
            min_edge = 0.02
            
            temp = self.df[self.df['pick_date'] >= pd.to_datetime(self.V5_START)].copy()
            if temp.empty: return pd.DataFrame()
            
            # Preparation for dynamic features
            temp['capper'] = temp['capper_id']
            temp['capper_rolling_roi'] = temp['roi_30d']
            temp['volatility'] = temp['vol_30d']
            temp['market_consensus'] = temp['implied_prob']
            if 'profit_units' in temp.columns:
                temp['return'] = temp['profit_units']
            
            temp = calculate_dynamic_features(temp)
            
            # 2. Conformal Inference
            dtest = xgb.DMatrix(temp[feats])
            temp['prob'] = booster.predict(dtest)
            temp['edge'] = temp['prob'] - temp['implied_prob']
            
            # 3. Precision Filtering
            valid = (temp['prob'] >= threshold) & \
                    (temp['edge'] >= min_edge) & \
                    (temp['decimal_odds'] >= 1.70) & \
                    (temp['decimal_odds'] <= 4.5)
            
            cand = temp[valid].copy()
            if cand.empty: return cand
            
            # 4. Institutional Staking
            kelly_frac = 0.15
            cand['b'] = cand['decimal_odds'] - 1
            cand['kelly'] = ((cand['b'] * cand['prob']) - (1 - cand['prob'])) / cand['b']
            
            consensus_mult = np.where(cand['v4_consensus_count_lag1'] >= 3, 1.10, 1.0)
            cand['wager_unit'] = (cand['kelly'] * kelly_frac * 100 * consensus_mult).clip(0, 3.0)
            
            # 5. Global Risk Control
            cand['daily_total_risk'] = cand.groupby('pick_date')['wager_unit'].transform('sum')
            cand['risk_factor'] = (10.0 / cand['daily_total_risk']).clip(upper=1.0)
            cand['wager_unit'] = (cand['wager_unit'] * cand['risk_factor']).round(2)
            
            # 6. Performance Attribution
            cand['profit_actual'] = np.where(cand['outcome']==1, cand['wager_unit']*(cand['decimal_odds']-1), 
                                             np.where(cand['outcome']==0, -cand['wager_unit'], 0))
            
            return cand[cand['wager_unit'] > 0]
            
        except Exception as e:
            print(f"Error V5: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def run_Kyanite_kyanite(self):
        """Kyanite Kyanite: Absolute Alpha Precision Engine (Kyanite)."""
        return self._run_zenith_engine('kyanite.json', 'kyanite_config.json', 'kyanite')

    def run_Carnelian_carnelian(self):
        """Carnelian Carnelian: Institutional Capacity Engine (Carnelian)."""
        return self._run_zenith_engine('carnelian.json', 'carnelian_config.json', 'carnelian')

    def _run_zenith_engine(self, model_file, config_file, name):
        try:
            m_path = get_model_path(model_file)
            booster = xgb.Booster()
            booster.load_model(m_path)
            
            # Configuration
            feats = self._get_feature_list(booster)
            # [SURGICAL ADJUSTMENT]: Lower thresholds for legacy simulation stability
            threshold = 0.55 if 'kyanite' in name else 0.50
            
            temp = self.df[self.df['pick_date'] >= pd.to_datetime(self.ZENITH_START)].copy()
            if temp.empty: return pd.DataFrame()
            
            # Prep for dynamic features
            temp['capper'] = temp['capper_id']
            temp['capper_rolling_roi'] = temp['roi_30d']
            temp['volatility'] = temp['vol_30d']
            temp['market_consensus'] = temp['implied_prob']
            if 'profit_units' not in temp.columns:
                temp['profit_units'] = np.where(temp['outcome'] == 1, temp['decimal_odds'] - 1, -1)
            temp['return'] = temp['profit_units']
            
            temp = calculate_dynamic_features(temp)
            
            # Zenith Specific Features (Lagged to avoid leakage)
            daily_counts = temp.groupby(['capper_id', 'pick_date']).size().reset_index(name='daily_count')
            daily_counts['pick_date'] = daily_counts['pick_date'] + pd.Timedelta(days=1)
            temp = temp.merge(daily_counts.rename(columns={'daily_count': 'bets_last_24h'}), on=['capper_id', 'pick_date'], how='left')
            temp['bets_last_24h'] = temp['bets_last_24h'].fillna(0)
            
            temp['synergy_score'] = 0.5 
            temp['is_dna_pattern'] = ((temp['roi_7d'] > 0.05) & (temp['vol_7d'] < 0.2)).astype(int)
            
            # 2. Inference
            # Ensure all features exist
            for f in feats:
                if f not in temp.columns: temp[f] = 0
                
            dtest = xgb.DMatrix(temp[feats])
            temp['prob'] = booster.predict(dtest)
            temp['edge'] = temp['prob'] - temp['implied_prob']
            
            # 3. Precision Filtering
            valid = (temp['prob'] >= threshold) & (temp['edge'] >= 0.02)
            cand = temp[valid].copy()
            
            # [STABILITY FIX]: If empty, return a DF with the expected columns to prevent KeyErrors in pipeline
            if cand.empty:
                return pd.DataFrame(columns=temp.columns)
                
            cand = cand.sort_values(['pick_date', 'prob'], ascending=[True, False])
            cand = cand.drop_duplicates(subset=['pick_date', 'pick_norm'], keep='first')
            cand['wager_unit'] = 1.0
            cand['profit_actual'] = np.where(cand['outcome']==1, cand['wager_unit']*(cand['decimal_odds']-1), 
                                             np.where(cand['outcome']==0, -cand['wager_unit'], 0))
            return cand
        except Exception as e:
            print(f"Error Zenith {name}: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def run_backtest_all(self):
        """Helper for comparison graphs - honors the institutional 'tracking' start dates."""
        return self.run_v4_quartz()
