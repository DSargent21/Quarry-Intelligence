import os
import pandas as pd
import numpy as np
import xgboost as xgb
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.calibration import calibration_curve
import json

# Set professional style
plt.style.use('seaborn-v0_8-muted')
sns.set_context("paper", font_scale=1.5)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['axes.grid'] = True

from src.pipeline import SportsDataPipeline, FeatureEngineer
from src.v5_dynamic_features import calculate_dynamic_features
from src.v5_conformal_sniper import ConformalSniperV5

def generate_assets():
    print("🎨 Generating Professional Research Assets for SAPPHIRE...")
    os.makedirs('docs/assets', exist_ok=True)
    
    # 1. Initialize and Fetch Data
    v5 = ConformalSniperV5(target_win_rate=0.60)
    pipeline = SportsDataPipeline()
    raw_df = pipeline.fetch_data_cached()
    engineer = FeatureEngineer(raw_df)
    df = engineer.process()
    
    # Prepare for dynamic features
    df['capper'] = df['capper_id']
    df['capper_rolling_roi'] = df['roi_30d']
    df['volatility'] = df['vol_30d']
    df['market_consensus'] = df['implied_prob']
    if 'profit_units' in df.columns:
        df['return'] = df['profit_units']
    df = calculate_dynamic_features(df)
    
    # Filter and Split
    df = df[df['outcome'].isin([0.0, 1.0])].copy()
    df['outcome'] = df['outcome'].astype(int)
    df = df.dropna(subset=v5.features).sort_values('pick_date')
    
    n = len(df)
    train_idx = int(n * 0.7)
    cal_idx = int(n * 0.85)
    
    train_df = df.iloc[:train_idx]
    cal_df = df.iloc[train_idx:cal_idx]
    test_df = df.iloc[cal_idx:]
    
    X_train, y_train = train_df[v5.features], train_df[v5.target]
    X_cal, y_cal = cal_df[v5.features], cal_df[v5.target]
    X_test, y_test = test_df[v5.features], test_df[v5.target]
    
    # 2. Train Model for Asset Generation
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
        'objective': 'binary:logistic'
    }
    model = xgb.train(params, dtrain, num_boost_round=200)
    
    # ---------------------------------------------------------
    # FIGURE 1: FEATURE IMPORTANCE (SHAP-STYLE)
    # ---------------------------------------------------------
    print("📊 Plotting Feature Importance...")
    importance = model.get_score(importance_type='gain')
    importance_df = pd.DataFrame({
        'Feature': importance.keys(),
        'Gain': importance.values()
    }).sort_values('Gain', ascending=False)
    
    plt.figure(figsize=(12, 8))
    sns.barplot(x='Gain', y='Feature', data=importance_df, palette='viridis')
    plt.title('SAPPHIRE v5: Feature Contribution (Information Gain)', fontsize=18, pad=20)
    plt.xlabel('Gain (Predictive Power Units)', fontsize=14)
    plt.tight_layout()
    plt.savefig('docs/assets/sapphire_importance.png', dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # FIGURE 2: CALIBRATION CURVE (RELIABILITY DIAGRAM)
    # ---------------------------------------------------------
    print("⚖️ Plotting Reliability Diagram...")
    probs = model.predict(dtest)
    fop, mpv = calibration_curve(y_test, probs, n_bins=10)
    
    plt.figure(figsize=(10, 10))
    plt.plot([0, 1], [0, 1], linestyle='--', color='gray', label='Perfectly Calibrated')
    plt.plot(mpv, fop, marker='.', markersize=15, linewidth=2, color='#1f77b4', label='SAPPHIRE v5')
    plt.title('Reliability Diagram: Probabilistic Calibration', fontsize=18, pad=20)
    plt.xlabel('Mean Predicted Probability', fontsize=14)
    plt.ylabel('Fraction of Positives (Observed Win Rate)', fontsize=14)
    plt.legend(fontsize=12)
    plt.tight_layout()
    plt.savefig('docs/assets/sapphire_calibration.png', dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # FIGURE 3: EQUITY CURVE (PROFIT OVER TIME)
    # ---------------------------------------------------------
    print("📈 Plotting Equity Curve...")
    test_df['prob'] = probs
    test_df['implied_prob'] = 1 / test_df['decimal_odds']
    test_df['edge'] = test_df['prob'] - test_df['implied_prob']
    
    # Re-calculate conformal threshold
    cal_probs = model.predict(dcal)
    thresholds = np.linspace(0.01, 0.99, 100)
    best_t = 0.99
    for t in thresholds:
        sel = cal_probs >= t
        if np.sum(sel) > 0 and np.mean(y_cal[sel]) >= 0.60:
            best_t = t
            break
            
    valid = (test_df['prob'] >= best_t) & (test_df['edge'] >= 0.02) & (test_df['decimal_odds'] <= 4.0)
    active = test_df[valid].copy()
    
    # Simple unit profit for curve
    active['profit'] = np.where(active['outcome'] == 1, active['decimal_odds'] - 1, -1.0)
    active['cum_profit'] = active['profit'].cumsum()
    
    plt.figure(figsize=(15, 7))
    plt.plot(active['pick_date'], active['cum_profit'], linewidth=3, color='#2ca02c')
    plt.fill_between(active['pick_date'], active['cum_profit'], color='#2ca02c', alpha=0.1)
    plt.title('Series 5: SAPPHIRE - Cumulative Alpha Generation', fontsize=18, pad=20)
    plt.ylabel('Net Units Profit', fontsize=14)
    plt.xlabel('Date Range (Holdout Period)', fontsize=14)
    plt.axhline(0, color='black', linestyle='-', alpha=0.3)
    plt.tight_layout()
    plt.savefig('docs/assets/sapphire_equity.png', dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # FIGURE 4: VOLUME & DENSITY
    # ---------------------------------------------------------
    print("📊 Plotting Volume Density...")
    plt.figure(figsize=(12, 6))
    daily_vol = active.groupby('pick_date').size()
    sns.histplot(daily_vol, bins=15, kde=True, color='#9467bd')
    plt.title('SAPPHIRE Execution Frequency (Bets Per Day)', fontsize=18, pad=20)
    plt.xlabel('Number of Bets Placed', fontsize=14)
    plt.ylabel('Frequency (Days)', fontsize=14)
    plt.tight_layout()
    plt.savefig('docs/assets/sapphire_volume.png', dpi=300)
    plt.close()

    print("✅ All research assets generated in docs/assets/")

if __name__ == "__main__":
    generate_assets()
