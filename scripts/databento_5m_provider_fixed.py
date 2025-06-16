#!/usr/bin/env python3
"""
Fixed Databento 5-minute data provider that handles futures market hours correctly
"""

import logging
import os
from datetime import datetime, timedelta
import pytz
import pandas as pd
from databento_5m_provider import Databento5MinuteProvider, aggregate_1min_to_5min

logger = logging.getLogger(__name__)

class FixedDatabento5MinuteProvider(Databento5MinuteProvider):
    """Fixed version that properly handles futures market hours"""

    def get_latest_bars(self, symbol: str = "NQM5", count: int = 50) -> pd.DataFrame:
        """
        Get the latest N 5-minute bars with proper futures market hour handling

        Futures markets: Sunday 6 PM ET to Friday 5 PM ET
        """
        now_utc = datetime.now(pytz.UTC)
        now_et = now_utc.astimezone(pytz.timezone('US/Eastern'))

        logger.info(f"Current time ET: {now_et}")

        # Determine if markets are currently open
        market_is_open = self._is_futures_market_open(now_et)

        if market_is_open:
            # Market is open - get recent data with a small delay for data availability
            end = now_utc - timedelta(minutes=15)  # 15-minute delay for data availability
            logger.info("Market is OPEN - fetching recent data")
        else:
            # Market is closed - get data from last trading session
            end = self._get_last_trading_session_end(now_et)
            logger.info(f"Market is CLOSED - fetching data from last session ending {end}")

        # Calculate start time based on number of bars needed
        # Add extra buffer for potential gaps
        minutes_needed = count * 5
        start = end - timedelta(minutes=minutes_needed + 120)  # 2 hour buffer

        # Get the data
        df = self.get_historical_5min_bars(symbol, start, end)

        # Return only the requested number of bars
        if len(df) > count:
            return df.iloc[-count:]
        return df

    def _is_futures_market_open(self, et_time: datetime) -> bool:
        """
        Check if futures market is open at given ET time

        Futures hours: Sunday 6 PM to Friday 5 PM ET
        """
        weekday = et_time.weekday()
        hour = et_time.hour

        # Sunday (6) - market opens at 6 PM
        if weekday == 6:
            return hour >= 18

        # Monday-Thursday (0-3) - market open all day
        elif weekday in [0, 1, 2, 3]:
            return True

        # Friday (4) - market closes at 5 PM
        elif weekday == 4:
            return hour < 17

        # Saturday (5) - market closed all day
        else:
            return False

    def _get_last_trading_session_end(self, et_time: datetime) -> datetime:
        """
        Get the end time of the last trading session
        """
        weekday = et_time.weekday()

        # If it's Saturday or Sunday before 6 PM, last session ended Friday 5 PM
        if weekday == 5 or (weekday == 6 and et_time.hour < 18):
            # Go back to Friday 5 PM
            days_back = weekday - 4 if weekday == 5 else 2
            last_friday = et_time - timedelta(days=days_back)
            last_close = last_friday.replace(hour=17, minute=0, second=0, microsecond=0)
            return last_close.astimezone(pytz.UTC)

        # If it's a weekday, check if before or after market hours
        if weekday in [0, 1, 2, 3, 4]:
            # For simplicity, use end of previous day
            yesterday = et_time - timedelta(days=1)
            # But if yesterday was Saturday, go to Friday
            if yesterday.weekday() == 5:
                yesterday = yesterday - timedelta(days=1)

            end_time = yesterday.replace(hour=23, minute=59, second=0, microsecond=0)
            return end_time.astimezone(pytz.UTC)

        # Default fallback
        return datetime.now(pytz.UTC) - timedelta(hours=24)

def test_fixed_provider():
    """Test the fixed provider"""
    print("Testing fixed data provider...")

    provider = FixedDatabento5MinuteProvider(enable_ifd_signals=False)

    # Test getting latest bars
    df = provider.get_latest_bars(symbol="NQM5", count=20)

    if df.empty:
        print("❌ Still no data returned")
    else:
        print(f"✅ Got {len(df)} bars!")
        print(f"Time range: {df.index[0]} to {df.index[-1]}")
        print(f"Last price: ${df['close'].iloc[-1]:,.2f}")

if __name__ == "__main__":
    test_fixed_provider()
