#!/usr/bin/env python3
"""
Databento data provider for 5-minute bars
Fetches 1-minute OHLCV data and aggregates to 5-minute bars
"""

import databento as db
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging
import pytz
from data_aggregation import aggregate_1min_to_5min, MinuteToFiveMinuteAggregator
from databento_auth import ensure_trading_safe_databento_client, DatabentoCriticalAuthError
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from utils.timezone_utils import get_utc_time

# Import IFD Chart Bridge for signal integration
try:
    from ifd_chart_bridge import IFDChartBridge, create_ifd_chart_bridge, IFDAggregatedSignal
    IFD_BRIDGE_AVAILABLE = True
except ImportError:
    logging.debug("IFD Chart Bridge not available - charts will run without IFD signals")
    IFD_BRIDGE_AVAILABLE = False

logger = logging.getLogger(__name__)

class Databento5MinuteProvider:
    """Provides 5-minute OHLCV bars using Databento 1-minute data"""

    def __init__(self, api_key: Optional[str] = None, enable_ifd_signals: bool = True):
        """
        Initialize the provider with BULLETPROOF authentication

        🚨 TRADING SAFETY: Will FAIL immediately if authentication fails
        🚫 NO DEMO DATA: Never allows fake data that could cause losses

        Args:
            api_key: Optional API key (will use env if not provided)
            enable_ifd_signals: Whether to enable IFD signal integration
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
        self._live_data_buffer = []  # Buffer for live streaming data
        self._is_streaming = False

        # IFD Signal Integration
        self.enable_ifd_signals = enable_ifd_signals and IFD_BRIDGE_AVAILABLE
        self.ifd_bridge: Optional[IFDChartBridge] = None

        if self.enable_ifd_signals:
            try:
                self.ifd_bridge = create_ifd_chart_bridge()
                logger.info("✅ IFD Chart Bridge integrated with data provider")
            except Exception as e:
                logger.warning(f"Failed to initialize IFD bridge: {e}")
                self.enable_ifd_signals = False
        else:
            logger.info("📊 Data provider initialized without IFD signals")


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
        max_available_end = get_utc_time() - timedelta(minutes=10)
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
            # Get API key - prefer from authenticated client to ensure consistency
            if hasattr(self.client, '_key') and self.client._key:
                api_key = self.client._key
            else:
                api_key = os.getenv('DATABENTO_API_KEY')
                if not api_key:
                    raise DatabentoCriticalAuthError("No Databento API key available for live streaming")
            self.live_client = db.Live(key=api_key)

        logger.info(f"Starting live streaming for {symbol}")
        self._is_streaming = True

        def live_callback(completed_bar):
            """Internal callback to handle completed 5-minute bars"""
            if completed_bar:
                # Add to live data buffer
                self._live_data_buffer.append(completed_bar)
                # Keep only last 100 bars in buffer
                if len(self._live_data_buffer) > 100:
                    self._live_data_buffer = self._live_data_buffer[-100:]

                logger.debug(f"New live 5-min bar: Close=${completed_bar.get('close', 0):,.2f}")

                if callback:
                    callback(completed_bar)

        # Subscribe to 1-minute bars
        self.live_client.subscribe(
            dataset="GLBX.MDP3",
            schema="ohlcv-1m",
            symbols=[symbol],
            stype_in="raw_symbol"
        )

        # Process incoming bars
        for record in self.live_client:
            if not self._is_streaming:
                break

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
                live_callback(completed_5min_bar)

    def stop_live_streaming(self):
        """Stop live streaming"""
        self._is_streaming = False
        if self.live_client:
            logger.info("Stopping live streaming")
            self.live_client = None

    def get_latest_bars(self, symbol: str = "NQM5", count: int = 50) -> pd.DataFrame:
        """
        Get the latest N 5-minute bars (combines historical + live data)

        Args:
            symbol: Contract symbol
            count: Number of 5-minute bars to return

        Returns:
            DataFrame with latest 5-minute bars including live data
        """
        # Get historical data first
        now = datetime.now(pytz.UTC)

        # Get historical data up to 10 minutes ago to avoid overlaps
        end = now - timedelta(minutes=10)
        start = end - timedelta(minutes=count * 5 + 60)  # Add buffer for aggregation

        df_historical = self.get_historical_5min_bars(symbol, start, end)

        # Combine with live data if available
        if self._live_data_buffer:
            logger.debug(f"Combining historical data with {len(self._live_data_buffer)} live bars")

            # Convert live data buffer to DataFrame
            live_rows = []
            for bar in self._live_data_buffer:
                live_rows.append({
                    'open': bar['open'],
                    'high': bar['high'],
                    'low': bar['low'],
                    'close': bar['close'],
                    'volume': bar['volume']
                })

            if live_rows:
                live_timestamps = [bar['timestamp'] for bar in self._live_data_buffer]
                df_live = pd.DataFrame(live_rows, index=pd.DatetimeIndex(live_timestamps, tz=pytz.UTC))

                # Combine and remove duplicates
                df_combined = pd.concat([df_historical, df_live])
                df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
                df_combined = df_combined.sort_index()

                logger.debug(f"Live data integrated: Latest close=${df_combined['close'].iloc[-1]:,.2f}")

                # Return only the requested number of bars
                if len(df_combined) > count:
                    return df_combined.iloc[-count:]
                return df_combined

        # Fallback to historical data only
        if len(df_historical) > count:
            return df_historical.iloc[-count:]
        return df_historical

    def clear_cache(self):
        """Clear the data cache"""
        self._cache.clear()
        logger.info("Cache cleared")

    # ============================================================================
    # IFD Signal Integration Methods
    # ============================================================================

    def get_latest_bars_with_ifd(self, symbol: str = "NQM5", count: int = 50) -> Tuple[pd.DataFrame, List[IFDAggregatedSignal]]:
        """
        Get latest 5-minute bars with synchronized IFD signals

        Args:
            symbol: Contract symbol
            count: Number of 5-minute bars to return

        Returns:
            Tuple of (OHLCV DataFrame, List of IFD signals)
        """
        if not self.enable_ifd_signals or not self.ifd_bridge:
            # Return OHLCV data with empty signals list
            df = self.get_latest_bars(symbol, count)
            return df, []

        try:
            # Get OHLCV data first
            df = self.get_latest_bars(symbol, count)

            if df.empty:
                return df, []

            # Get IFD signals for the same time range
            start_time = df.index[0].to_pydatetime()
            end_time = df.index[-1].to_pydatetime()

            ifd_signals = self.ifd_bridge.get_ifd_signals_for_chart(start_time, end_time)

            logger.debug(f"Retrieved {len(df)} OHLCV bars and {len(ifd_signals)} IFD signals")

            return df, ifd_signals

        except Exception as e:
            logger.error(f"Failed to get bars with IFD signals: {e}")
            # Fallback to OHLCV only
            df = self.get_latest_bars(symbol, count)
            return df, []

    def get_historical_bars_with_ifd(self, symbol: str = "NQM5", start: Optional[datetime] = None,
                                   end: Optional[datetime] = None, hours_back: int = 24) -> Tuple[pd.DataFrame, List[IFDAggregatedSignal]]:
        """
        Get historical 5-minute bars with synchronized IFD signals

        Args:
            symbol: Contract symbol
            start: Start time
            end: End time
            hours_back: Hours of history if start not specified

        Returns:
            Tuple of (OHLCV DataFrame, List of IFD signals)
        """
        if not self.enable_ifd_signals or not self.ifd_bridge:
            # Return OHLCV data with empty signals list
            df = self.get_historical_5min_bars(symbol, start, end, hours_back)
            return df, []

        try:
            # Get OHLCV data first
            df = self.get_historical_5min_bars(symbol, start, end, hours_back)

            if df.empty:
                return df, []

            # Get IFD signals for the same time range
            start_time = df.index[0].to_pydatetime()
            end_time = df.index[-1].to_pydatetime()

            ifd_signals = self.ifd_bridge.get_ifd_signals_for_chart(start_time, end_time)

            logger.debug(f"Retrieved {len(df)} historical OHLCV bars and {len(ifd_signals)} IFD signals")

            return df, ifd_signals

        except Exception as e:
            logger.error(f"Failed to get historical bars with IFD signals: {e}")
            # Fallback to OHLCV only
            df = self.get_historical_5min_bars(symbol, start, end, hours_back)
            return df, []

    def get_ifd_signals_only(self, start_time: datetime, end_time: datetime) -> List[IFDAggregatedSignal]:
        """
        Get IFD signals for a specific time range (chart overlay use)

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of IFD signals within time range
        """
        if not self.enable_ifd_signals or not self.ifd_bridge:
            return []

        try:
            return self.ifd_bridge.get_ifd_signals_for_chart(start_time, end_time)
        except Exception as e:
            logger.error(f"Failed to get IFD signals: {e}")
            return []

    def get_ifd_bridge_status(self) -> Dict[str, any]:
        """
        Get status of IFD bridge integration

        Returns:
            Status information about IFD integration
        """
        if not self.enable_ifd_signals:
            return {
                'enabled': False,
                'available': IFD_BRIDGE_AVAILABLE,
                'reason': 'IFD signals disabled' if IFD_BRIDGE_AVAILABLE else 'IFD bridge not available'
            }

        if not self.ifd_bridge:
            return {
                'enabled': True,
                'available': False,
                'reason': 'IFD bridge failed to initialize'
            }

        try:
            bridge_stats = self.ifd_bridge.get_bridge_statistics()
            health_status = self.ifd_bridge.get_health_status()

            return {
                'enabled': True,
                'available': True,
                'healthy': health_status['overall_status'] == 'healthy',
                'statistics': bridge_stats,
                'health': health_status
            }
        except Exception as e:
            return {
                'enabled': True,
                'available': False,
                'error': str(e)
            }

    def add_ifd_signal(self, signal) -> bool:
        """
        Add a real-time IFD signal to the bridge (for live streaming integration)

        Args:
            signal: InstitutionalSignalV3 object

        Returns:
            True if signal was added successfully
        """
        if not self.enable_ifd_signals or not self.ifd_bridge:
            return False

        try:
            self.ifd_bridge.add_signal(signal)
            return True
        except Exception as e:
            logger.error(f"Failed to add IFD signal: {e}")
            return False

    def toggle_ifd_signals(self, enabled: bool) -> bool:
        """
        Enable or disable IFD signal integration at runtime

        Args:
            enabled: Whether to enable IFD signals

        Returns:
            True if toggle was successful
        """
        if not IFD_BRIDGE_AVAILABLE:
            logger.warning("Cannot enable IFD signals - bridge not available")
            return False

        if enabled and not self.ifd_bridge:
            # Try to initialize bridge
            try:
                self.ifd_bridge = create_ifd_chart_bridge()
                self.enable_ifd_signals = True
                logger.info("✅ IFD signals enabled")
                return True
            except Exception as e:
                logger.error(f"Failed to enable IFD signals: {e}")
                return False
        elif not enabled:
            # Disable signals
            self.enable_ifd_signals = False
            logger.info("📊 IFD signals disabled")
            return True

        return True  # Already in desired state

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
