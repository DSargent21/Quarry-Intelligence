import pandas as pd
import numpy as np
from .logger import logger

class DataValidator:
    REQUIRED_COLUMNS = [
        'id', 'pick_date', 'pick_value', 'unit', 'odds_american', 'league_id', 'capper_id'
    ]
    
    EXPECTED_LEAGUES = ['NBA', 'NCAAB', 'NFL', 'NCAAF', 'NHL', 'MLB', 'Combat', 'Soccer', 'Tennis', 'Other']

    @staticmethod
    def validate_raw_data(df: pd.DataFrame) -> bool:
        """Checks if the raw data from Supabase meets the minimum requirements."""
        if df.empty:
            logger.error("Data Validation Failed: DataFrame is empty.")
            return False
            
        missing = [col for col in DataValidator.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            logger.error(f"Data Validation Failed: Missing columns: {missing}")
            return False
            
        # Check for extreme null counts in critical columns
        critical_cols = ['pick_date', 'odds_american', 'capper_id']
        for col in critical_cols:
            null_pct = df[col].isnull().mean()
            if null_pct > 0.5:
                logger.warning(f"Data Validation Alert: {col} has {null_pct:.1%} null values.")
                
        return True

    @staticmethod
    def validate_processed_features(df: pd.DataFrame, features: list) -> bool:
        """Ensures all required features for a model are present and numeric."""
        missing = [f for f in features if f not in df.columns]
        if missing:
            logger.error(f"Feature Validation Failed: Missing required features: {missing}")
            return False
            
        # Check for NaNs in feature columns
        for f in features:
            if df[f].isnull().any():
                logger.warning(f"Feature '{f}' contains NaNs. Filling with defaults.")
                df[f] = df[f].fillna(0)
                
        return True

    @staticmethod
    def validate_stats_json(stats: dict) -> bool:
        """Validates the final stats dictionary before saving."""
        if "models" not in stats or "meta" not in stats:
            return False
        for model in stats["models"]:
            # Ensure ROI and Net are present and numeric
            m = stats["models"][model]
            if "roi" not in m or "net" not in m:
                logger.error(f"Stats Validation Failed: Model {model} missing key metrics.")
                return False
        return True
