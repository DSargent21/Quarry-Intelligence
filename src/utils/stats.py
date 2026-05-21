import pandas as pd
import numpy as np
from datetime import datetime

class StatsEngine:
    """Centralized engine for calculating model performance metrics consistently."""

    @staticmethod
    def get_et_now():
        """Returns the current time in US/Eastern timezone."""
        try:
            return pd.Timestamp.now(tz='US/Eastern')
        except:
            # Fallback for systems without zoneinfo (using UTC-4 for May)
            return pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=4)

    @staticmethod
    def calculate_metrics(df):
        """Calculates standard metrics for a model's simulated picks."""
        if df is None or df.empty:
            return {
                "roi": 0.0, "net": 0.0, "wins": 0, "losses": 0, "pushes": 0,
                "record": "0-0-0", "win_rate": 0.0, "sample": 0, "volume": "None (0 bets/day)"
            }

        # Filter for settled bets (1.0 = Win, 0.0 = Loss, 0.5 = Push)
        settled = df[df['outcome'].isin([0.0, 1.0, 0.5])].copy()
        
        if settled.empty:
            return {
                "roi": 0.0, "net": 0.0, "wins": 0, "losses": 0, "pushes": 0,
                "record": "0-0-0", "win_rate": 0.0, "sample": len(df), "volume": "None (0 bets/day)"
            }

        net = settled['profit_actual'].sum()
        wager = settled['wager_unit'].sum()
        roi = (net / wager) if wager > 0 else 0.0
        
        wins = len(settled[settled['outcome'] == 1.0])
        losses = len(settled[settled['outcome'] == 0.0])
        pushes = len(settled[settled['outcome'] == 0.5])
        
        total_settled_decisive = wins + losses
        win_rate = (wins / total_settled_decisive) if total_settled_decisive > 0 else 0.0
        
        # Calculate volume category
        volume_text = "None (0 bets/day)"
        if 'pick_date' in df.columns and not df.empty:
            days = (df['pick_date'].max() - df['pick_date'].min()).days + 1
            avg = len(df) / max(days, 1)
            
            if avg > 50: cat = "Very High"
            elif avg > 20: cat = "High"
            elif avg > 10: cat = "Medium"
            elif avg > 5: cat = "Low"
            else: cat = "Very Low"
            volume_text = f"{cat} (~{int(avg)} bets/day)"

        return {
            "roi": roi, # Decimal form (0.187 for 18.7%)
            "net": net,
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "record": f"{wins}-{losses}-{pushes}",
            "win_rate": win_rate,
            "sample": len(df),
            "volume": volume_text
        }

    @staticmethod
    def get_yesterday_data(df, et_now=None):
        """Extracts data for 'Yesterday' relative to US/Eastern time."""
        if df is None or df.empty or 'pick_date' not in df.columns:
            return None

        if et_now is None:
            et_now = StatsEngine.get_et_now()
            
        yesterday_date = (et_now - pd.Timedelta(days=1)).date()
        
        # Ensure pick_date is comparable (date only)
        # Handle case where pick_date might have timezone info
        if df['pick_date'].dt.tz is not None:
            day_df = df[df['pick_date'].dt.tz_convert('US/Eastern').dt.date == yesterday_date].copy()
        else:
            day_df = df[df['pick_date'].dt.date == yesterday_date].copy()
            
        if day_df.empty:
            # If no data for calendar yesterday, fallback to the last day with action
            last_date = df['pick_date'].max().date()
            if df['pick_date'].dt.tz is not None:
                day_df = df[df['pick_date'].dt.tz_convert('US/Eastern').dt.date == last_date].copy()
            else:
                day_df = df[df['pick_date'].dt.date == last_date].copy()
            yesterday_date = last_date

        # Calculate day metrics
        metrics = StatsEngine.calculate_metrics(day_df)
        
        # Format ledger items for UI
        ledger = []
        # Sort by profit descending (Wins first)
        sort_cols = [c for c in ['profit_actual', 'decimal_odds', 'edge'] if c in day_df.columns]
        day_sorted = day_df.sort_values(sort_cols, ascending=False) if sort_cols else day_df
        
        for _, r in day_sorted.head(20).iterrows():
            odds = 0
            if 'odds_american' in r and pd.notna(r['odds_american']):
                odds = int(r['odds_american'])
            elif 'decimal_odds' in r:
                dec = r['decimal_odds']
                odds = int((dec-1)*100) if dec >= 2.0 else int(-100/(dec-1))
                
            ledger.append({
                "date": r['pick_date'].strftime('%m/%d'),
                "league": r.get('league_name', 'N/A'),
                "selection": r.get('pick_norm', r.get('pick_value', 'N/A')),
                "odds": odds,
                "wager": round(r['wager_unit'], 2),
                "profit": round(r['profit_actual'], 2),
                "result": "WIN" if r['outcome']==1.0 else "LOSS" if r['outcome']==0.0 else "PUSH",
                "edge": float(r.get('edge', 0.0))
            })

        return {
            "date": yesterday_date.strftime('%b %d, %Y'),
            "record": metrics['record'],
            "win_rate": round(metrics['win_rate'] * 100, 1),
            "net": round(metrics['net'], 2),
            "roi": round(metrics['roi'] * 100, 1),
            "ledger": ledger
        }
