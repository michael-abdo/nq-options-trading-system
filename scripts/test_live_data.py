#!/usr/bin/env python3
"""
Test live data fetching during market hours
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from databento_5m_provider import Databento5MinuteProvider
from datetime import datetime, timedelta
import pytz
import pandas as pd

def test_live_data():
    print("🔍 Testing Live Data Fetch")
    print("=" * 60)

    # Initialize provider
    print("\n1. Initializing data provider...")
    provider = Databento5MinuteProvider(enable_ifd_signals=False)

    # Get current time info
    now_utc = datetime.now(pytz.UTC)
    now_et = now_utc.astimezone(pytz.timezone('US/Eastern'))
    print(f"\nCurrent time (ET): {now_et}")
    print(f"Day: {now_et.strftime('%A')}")

    # Try different time ranges
    print("\n2. Testing different time ranges...")

    # Test 1: Last 4 hours
    print("\n📊 Test 1: Last 4 hours (48 bars)")
    df1 = provider.get_latest_bars(symbol="NQM5", count=48)
    print(f"Result: {len(df1)} bars returned")
    if not df1.empty:
        print(f"Time range: {df1.index[0]} to {df1.index[-1]}")
        print(f"Last price: ${df1['close'].iloc[-1]:,.2f}")

    # Test 2: Last 1 hour
    print("\n📊 Test 2: Last 1 hour (12 bars)")
    df2 = provider.get_latest_bars(symbol="NQM5", count=12)
    print(f"Result: {len(df2)} bars returned")

    # Test 3: Specific time range
    print("\n📊 Test 3: Specific time range (last trading day)")
    # Go back to last Friday if it's Monday morning
    if now_et.weekday() == 0 and now_et.hour < 6:  # Monday before 6 AM
        end_time = now_et.replace(hour=17, minute=0, second=0, microsecond=0)
        end_time = end_time - timedelta(days=3)  # Last Friday
    else:
        end_time = now_utc

    start_time = end_time - timedelta(hours=2)

    print(f"Requesting data from {start_time} to {end_time}")
    df3 = provider.get_5m_bars(
        symbol="NQM5",
        start_time=start_time,
        end_time=end_time
    )
    print(f"Result: {len(df3)} bars returned")

    # Test 4: Check raw Databento response
    print("\n📊 Test 4: Raw Databento API test")
    try:
        from databento import Historical
        client = Historical()

        # Test with 1-minute bars first
        print("Testing 1-minute bars...")
        test_end = now_utc
        test_start = test_end - timedelta(hours=1)

        df_test = client.timeseries.get_range(
            dataset="GLBX.MDP3",
            symbols=["NQM5"],
            stype_in="continuous",
            start=test_start,
            end=test_end,
            schema="ohlcv-1m"
        ).to_df()

        print(f"Raw API returned: {len(df_test)} bars")
        if not df_test.empty:
            print(f"Latest bar: {df_test.index[-1]}")

    except Exception as e:
        print(f"Raw API test failed: {e}")

    # Test 5: Try different symbols
    print("\n📊 Test 5: Testing different symbols")
    symbols = ["NQM5", "NQZ5", "ESM5", "NQ.c.0"]
    for symbol in symbols:
        df = provider.get_latest_bars(symbol=symbol, count=5)
        print(f"{symbol}: {len(df)} bars returned")

    # Diagnosis
    print("\n🔧 Diagnosis:")
    if all(df.empty for df in [df1, df2, df3]):
        print("❌ No data returned from any query")
        print("\nPossible issues:")
        print("1. Symbol might be incorrect (try NQZ5 for December)")
        print("2. API key might not have access to futures data")
        print("3. Time range might be outside trading hours")
        print("4. Databento dataset might be wrong")
    else:
        print("✅ Data is available!")

if __name__ == "__main__":
    test_live_data()
