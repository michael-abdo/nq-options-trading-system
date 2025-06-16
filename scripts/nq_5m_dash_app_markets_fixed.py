#!/usr/bin/env python3
"""
NQ Futures Dashboard with proper futures market hours handling
Fixes the issue where Monday morning shows no data even though markets opened Sunday 6 PM
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Import and patch the data provider BEFORE using it
from databento_5m_provider import Databento5MinuteProvider
import pandas as pd
from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)

# Create patched get_latest_bars method
def patched_get_latest_bars(self, symbol: str = "NQM5", count: int = 50) -> pd.DataFrame:
    """
    Fixed version that properly handles futures market hours
    Futures: Sunday 6 PM to Friday 5 PM ET
    """
    now_utc = datetime.now(pytz.UTC)
    now_et = now_utc.astimezone(pytz.timezone('US/Eastern'))

    logger.info(f"Fetching bars at {now_et} ET")

    # Determine if futures market is currently open
    weekday = now_et.weekday()
    hour = now_et.hour

    market_is_open = False
    if weekday == 6 and hour >= 18:  # Sunday after 6 PM
        market_is_open = True
    elif weekday in [0, 1, 2, 3]:  # Monday-Thursday
        market_is_open = True
    elif weekday == 4 and hour < 17:  # Friday before 5 PM
        market_is_open = True

    if market_is_open:
        # Market is open - get recent data
        # Use 15-minute delay for data availability
        end = now_utc - timedelta(minutes=15)
        logger.info(f"Market OPEN - fetching data up to {end}")
    else:
        # Market is closed - get last trading session
        if weekday == 5 or (weekday == 6 and hour < 18):
            # Weekend - go back to Friday 5 PM
            days_back = weekday - 4 if weekday == 5 else 2
            last_friday = now_et - timedelta(days=days_back)
            end = last_friday.replace(hour=17, minute=0, second=0, microsecond=0)
            end = end.astimezone(pytz.UTC)
            logger.info(f"Market CLOSED - using Friday close at {end}")
        else:
            # Shouldn't happen with above logic
            end = now_utc - timedelta(hours=24)

    # Calculate start time
    minutes_needed = count * 5 + 120  # Add 2-hour buffer
    start = end - timedelta(minutes=minutes_needed)

    # Get historical bars
    df = self.get_historical_5min_bars(symbol, start, end)

    # Return requested count
    if len(df) > count:
        return df.iloc[-count:]
    return df

# Apply the patch
Databento5MinuteProvider.get_latest_bars = patched_get_latest_bars

# Now import the rest of the dashboard
from nq_5m_dash_app_ifd import NQDashAppIFD

class MarketAwareNQDashApp(NQDashAppIFD):
    """Enhanced dashboard that properly handles futures market hours"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("Market-aware dashboard initialized with futures hours fix")

def main():
    """Run the market-aware dashboard"""
    import argparse

    parser = argparse.ArgumentParser(description='Market-aware NQ Dashboard')
    parser.add_argument('--symbol', default='NQM5', help='Contract symbol')
    parser.add_argument('--hours', type=int, default=4, help='Hours of data')
    parser.add_argument('--port', type=int, default=8050, help='Port number')
    parser.add_argument('--debug', action='store_true', help='Debug mode')

    args = parser.parse_args()

    print("🚀 Starting Market-Aware NQ Dashboard")
    print("📊 Features:")
    print("   ✅ Proper futures market hours (Sun 6PM - Fri 5PM ET)")
    print("   ✅ Real-time data during market hours")
    print("   ✅ IFD signal integration")
    print("   ✅ Automatic fallback to demo mode when needed")
    print()

    app = MarketAwareNQDashApp(
        symbol=args.symbol,
        hours=args.hours,
        port=args.port
    )

    app.run(debug=args.debug)

if __name__ == "__main__":
    main()
