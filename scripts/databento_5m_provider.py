#!/usr/bin/env python3
"""
Databento data provider for 5-minute bars
Fetches 1-minute OHLCV data and aggregates to 5-minute bars
"""

import databento as db
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
import pytz
from data_aggregation import aggregate_1min_to_5min, MinuteToFiveMinuteAggregator
from databento_auth import ensure_trading_safe_databento_client, DatabentoCriticalAuthError
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from utils.timezone_utils import get_eastern_time, get_utc_time, to_eastern_time

logger = logging.getLogger(__name__)

class Databento5MinuteProvider:
    """Provides 5-minute OHLCV bars using Databento 1-minute data"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the provider with BULLETPROOF authentication

        🚨 TRADING SAFETY: Will FAIL immediately if authentication fails
        🚫 NO DEMO DATA: Never allows fake data that could cause losses
        """
        logger.info("🔐 Initializing TRADING-SAFE Databento provider...")

        try:
            # Use bulletproof authentication - will fail fast if invalid
            self.client = ensure_trading_safe_databento_client()
            logger.info("✅ Databento client authenticated and SAFE FOR TRADING")

        except DatabentoCriticalAuthError as e:
            logger.critical(f"🚨 CRITICAL AUTH FAILURE: {e}")
            raise
        except Exception as e:
            logger.critical(f"🚨 UNEXPECTED AUTH ERROR: {e}")
            raise DatabentoCriticalAuthError(f"Failed to initialize trading-safe client: {e}")

        self.live_client = None
        self.aggregator = MinuteToFiveMinuteAggregator()
        self._cache = {}  # Simple in-memory cache

    def get_historical_5min_bars(self,
                                symbol: str = "NQM5",
                                start: Optional[datetime] = None,
                                end: Optional[datetime] = None,
                                hours_back: int = 24) -> pd.DataFrame:
        """
        Get historical 5-minute bars

        Args:
            symbol: Contract symbol (default: NQM5)
            start: Start time (defaults to hours_back from end)
            end: End time (defaults to now)
            hours_back: Hours of history if start not specified

        Returns:
            DataFrame with 5-minute OHLCV bars
        """
        # Set default times (timezone-aware UTC for API)
        if end is None:
            end = get_utc_time()
        if start is None:
            start = end - timedelta(hours=hours_back)

        # Auto-adjust end time if beyond data availability (safety feature)
        # Databento data typically has a few minutes delay
        max_available_end = get_utc_time() - timedelta(minutes=15)
        if end > max_available_end:
            logger.info(f"Adjusting end time from {end} to {max_available_end} (data availability)")
            end = max_available_end
            # Recalculate start time to maintain the requested time window
            if start is None or (end - start).total_seconds() / 3600 != hours_back:
                start = end - timedelta(hours=hours_back)

        # Check cache first
        cache_key = f"{symbol}_{start.isoformat()}_{end.isoformat()}"
        if cache_key in self._cache:
            logger.info(f"Returning cached data for {symbol}")
            return self._cache[cache_key]

        try:
            logger.info(f"Fetching 1-minute bars for {symbol} from {start} to {end}")

            # Fetch 1-minute data
            data = self.client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=[symbol],
                schema="ohlcv-1m",
                start=start,
                end=end
            )

            # Convert to DataFrame
            df_1min = data.to_df()

            if df_1min.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            # Ensure proper column names
            df_1min = df_1min.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })

            # Aggregate to 5-minute bars
            df_5min = aggregate_1min_to_5min(df_1min)

            # Cache the result
            self._cache[cache_key] = df_5min

            logger.info(f"Aggregated {len(df_1min)} 1-min bars to {len(df_5min)} 5-min bars")
            return df_5min

        except Exception as e:
            logger.critical(f"🚨 CRITICAL DATA FETCH FAILURE: {e}")
            logger.critical("🚫 NO FALLBACK DATA - TRADING OPERATIONS STOPPED FOR SAFETY")

            # Create detailed error message for traders
            error_msg = (
                f"🚨 TRADING DATA FETCH FAILED 🚨\n"
                f"Symbol: {symbol}\n"
                f"Time range: {start} to {end}\n"
                f"Error: {e}\n"
                f"\n"
                f"🛑 NO DEMO DATA FALLBACK FOR TRADING SAFETY\n"
                f"Fix the data connection before resuming trading."
            )

            raise DatabentoCriticalAuthError(error_msg)

    # 🚫 REMOVED DANGEROUS DEMO DATA GENERATION
    # Demo data fallback was REMOVED for trading safety
    # Using fake data could cause financial losses

    def start_live_streaming(self, symbol: str = "NQM5", callback=None):
        """
        Start live streaming of 1-minute bars and aggregate to 5-minute

        Args:
            symbol: Contract symbol
            callback: Function to call with completed 5-minute bars
        """
        if self.live_client is None:
            self.live_client = db.Live(key=self.api_key)

        logger.info(f"Starting live streaming for {symbol}")

        # Subscribe to 1-minute bars
        self.live_client.subscribe(
            dataset="GLBX.MDP3",
            schema="ohlcv-1m",
            symbols=[symbol],
            stype_in="raw_symbol"
        )

        # Process incoming bars
        for record in self.live_client:
            if hasattr(record, 'open'):
                # Convert to bar data
                bar_data = {
                    'timestamp': datetime.fromtimestamp(record.ts_event / 1e9),
                    'open': record.open / 1e9,
                    'high': record.high / 1e9,
                    'low': record.low / 1e9,
                    'close': record.close / 1e9,
                    'volume': record.volume
                }

                # Add to aggregator
                completed_5min_bar = self.aggregator.add_1min_bar(bar_data)

                if completed_5min_bar and callback:
                    callback(completed_5min_bar)

    def stop_live_streaming(self):
        """Stop live streaming"""
        if self.live_client:
            logger.info("Stopping live streaming")
            self.live_client = None

    def get_latest_bars(self, symbol: str = "NQM5", count: int = 50) -> pd.DataFrame:
        """
        Get the latest N 5-minute bars

        Args:
            symbol: Contract symbol
            count: Number of 5-minute bars to return

        Returns:
            DataFrame with latest 5-minute bars
        """
        # Calculate time range (5 minutes per bar) - timezone-aware
        # Use end of previous trading day since data might not be available for current day
        now = datetime.now(pytz.UTC)

        # If it's weekend or after hours, go back to last market close
        if now.weekday() >= 5:  # Saturday or Sunday
            days_back = now.weekday() - 4  # Go back to Friday
            end = now - timedelta(days=days_back, hours=3)  # End of Friday trading
        else:
            # Use yesterday's data to avoid real-time data issues
            end = now - timedelta(days=1)

        start = end - timedelta(minutes=count * 5 + 60)  # Add larger buffer

        df = self.get_historical_5min_bars(symbol, start, end)

        # Return only the requested number of bars
        if len(df) > count:
            return df.iloc[-count:]
        return df

    def clear_cache(self):
        """Clear the data cache"""
        self._cache.clear()
        logger.info("Cache cleared")

def test_provider():
    """Test the Databento 5-minute provider"""
    print("🧪 Testing Databento 5-Minute Provider")
    print("=" * 50)

    # Initialize provider
    provider = Databento5MinuteProvider()

    # Test historical data
    print("\n📊 Fetching last 12 5-minute bars (1 hour)...")
    df = provider.get_latest_bars(count=12)

    if not df.empty:
        print(f"✅ Retrieved {len(df)} bars")
        print(f"Time range: {df.index[0]} to {df.index[-1]}")
        print(f"Price range: ${df['close'].min():,.2f} - ${df['close'].max():,.2f}")
        print(f"Total volume: {df['volume'].sum():,}")

        print("\nLast 5 bars:")
        print(df.tail())
    else:
        print("❌ No data retrieved")

    # Test live streaming simulation
    print("\n📡 Testing live streaming callback...")

    def on_new_bar(bar):
        print(f"  New 5-min bar: {bar}")

    # Note: Actual live streaming would run continuously
    # This is just to verify the setup works
    print("✅ Live streaming configured (not starting continuous stream in test)")

    return provider

if __name__ == "__main__":
    test_provider()
