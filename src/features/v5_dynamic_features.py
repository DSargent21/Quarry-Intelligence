def calculate_dynamic_features(df):
    """
    Add 2‑3 radical dynamic features to the DataFrame.
    Features are computed using only information known at pick_date (T‑1) to avoid leakage.

    Assumptions about input DataFrame columns:
    - pick_date : datetime or string – date of the pick.
    - capper    : identifier for the capper.
    - return    : numeric profit/loss for each pick (optional; if missing, momentum is computed from rolling ROI).
    - capper_rolling_roi : already computed long‑term rolling ROI for the capper.
    - volatility           : already computed rolling volatility of returns for the capper.
    - market_consensus    : market‑implied probability (0‑1) of the pick succeeding.

    New features:
    1. roi_volatility_ratio   – risk‑adjusted ROI (ROI / volatility).
    2. consensus_roi_spread   – difference between capper's ROI and the ROI implied by market consensus
                               (assuming even‑money odds). Captures the capper's edge over the market.
    3. roi_momentum           – short‑term ROI (5‑game rolling mean of past returns) minus the long‑term
                               rolling ROI. If the 'return' column is missing, momentum is approximated by
                               the first‑order change in the rolling ROI.

    Returns
    -------
    pd.DataFrame
        DataFrame with the three new columns added.
    """
    import pandas as pd
    import numpy as np

    # ------------------------------------------------------------------
    # Ensure chronological order per capper (prevent look‑ahead bias)
    # ------------------------------------------------------------------
    df = df.sort_values(['capper', 'pick_date']).reset_index(drop=True)

    # ------------------------------------------------------------------
    # 1. Risk‑adjusted ROI (ROI / volatility)
    # ------------------------------------------------------------------
    eps = 1e-8  # avoid division by zero
    df['roi_volatility_ratio'] = df['capper_rolling_roi'] / (df['volatility'].abs() + eps)

    # ------------------------------------------------------------------
    # 2. Consensus‑ROI spread
    #    Assume market_consensus is a probability (0‑1). For even‑money odds (2.0),
    #    implied ROI = 2 * consensus - 1. The spread = capper ROI - implied ROI.
    # ------------------------------------------------------------------
    df['consensus_roi_spread'] = df['capper_rolling_roi'] - (2 * df['market_consensus'] - 1)

    # ------------------------------------------------------------------
    # 3. ROI momentum
    #    Short‑term ROI = rolling mean of *previous* returns (shift(1) to avoid leakage).
    #    If 'return' column is absent, fall back to the change in rolling ROI.
    # ------------------------------------------------------------------
    if 'return' in df.columns:
        # Short‑term (5‑game) rolling mean of past returns, shifted to exclude the current pick
        df['short_roi'] = df.groupby('capper')['return'].transform(
            lambda x: x.shift(1).rolling(window=5, min_periods=1).mean()
        )
        # Momentum = short‑term ROI - long‑term ROI
        df['roi_momentum'] = df['short_roi'] - df['capper_rolling_roi']
        df.drop(columns=['short_roi'], inplace=True)
    else:
        # Fallback: use the change in rolling ROI as a proxy for momentum
        df['roi_momentum'] = df.groupby('capper')['capper_rolling_roi'].transform(lambda x: x.diff())

    # ------------------------------------------------------------------
    # Clean‑up: replace infinities / NaNs with 0 (neutral) – adjust as needed
    # ------------------------------------------------------------------
    for col in ['roi_volatility_ratio', 'consensus_roi_spread', 'roi_momentum']:
        df[col] = df[col].replace([np.inf, -np.inf], np.nan).fillna(0)

    return df