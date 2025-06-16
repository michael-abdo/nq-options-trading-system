#!/usr/bin/env python3
"""
Diagnose why we're not getting live market data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from databento_5m_provider import Databento5MinuteProvider
from datetime import datetime, timedelta
import pytz
import pandas as pd

def diagnose_market_data():
    print("🔍 Market Data Diagnosis")
    print("=" * 60)

    # Current time analysis
    now_utc = datetime.now(pytz.UTC)
    now_et = now_utc.astimezone(pytz.timezone('US/Eastern'))

    print(f"\n📅 Current Time Analysis:")
    print(f"UTC: {now_utc}")
    print(f"ET:  {now_et}")
    print(f"Day: {now_et.strftime('%A')}")

    # Market status
    market_open_time = datetime(2025, 6, 15, 18, 0, tzinfo=pytz.timezone('US/Eastern'))  # Sunday 6 PM
    hours_since_open = (now_et - market_open_time).total_seconds() / 3600

    print(f"\n📊 Market Status:")
    print(f"Market opened: {market_open_time} ({hours_since_open:.1f} hours ago)")
    print(f"Status: OPEN ✅")

    # Initialize provider
    print("\n🔧 Testing Data Provider...")
    provider = Databento5MinuteProvider(enable_ifd_signals=False)

    # Test 1: Try to get data from when market opened
    print("\n Test 1: Data from market open (Sunday 6 PM)")
    start_1 = market_open_time
    end_1 = start_1 + timedelta(hours=2)
    print(f"Requesting: {start_1} to {end_1}")

    try:
        # Try raw API call
        from databento import Historical
        client = Historical()

        df1 = client.timeseries.get_range(
            dataset="GLBX.MDP3",
            symbols=["NQM5"],
            stype_in="continuous",
            start=start_1.astimezone(pytz.UTC),
            end=end_1.astimezone(pytz.UTC),
            schema="ohlcv-1m"
        ).to_df()
        print(f"Result: {len(df1)} bars")
        if not df1.empty:
            print(f"First bar: {df1.index[0]}")
            print(f"Last bar: {df1.index[-1]}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: Try last Friday's data
    print("\n Test 2: Last Friday's close")
    friday_close = datetime(2025, 6, 13, 17, 0, tzinfo=pytz.timezone('US/Eastern'))
    friday_start = friday_close - timedelta(hours=2)
    print(f"Requesting: {friday_start} to {friday_close}")

    df2 = provider.get_latest_bars(symbol="NQM5", count=24)
    print(f"Result: {len(df2)} bars")

    # Test 3: Check different contract months
    print("\n Test 3: Different contract months")
    contracts = {
        "NQM5": "June 2025",
        "NQU5": "September 2025",
        "NQZ5": "December 2025",
        "NQH6": "March 2026",
        "NQ.c.0": "Continuous front month"
    }

    for symbol, desc in contracts.items():
        df = provider.get_latest_bars(symbol=symbol, count=5)
        status = "✅ Data available" if not df.empty else "❌ No data"
        print(f"{symbol} ({desc}): {status}")
        if not df.empty:
            print(f"  Last price: ${df['close'].iloc[-1]:,.2f}")
            print(f"  Last bar: {df.index[-1]}")

    # Test 4: Check data availability by going back in time
    print("\n Test 4: Data availability timeline")
    for hours_back in [1, 6, 12, 24, 48, 72]:
        end_time = now_utc - timedelta(hours=hours_back)
        start_time = end_time - timedelta(hours=1)

        try:
            df = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQM5"],
                stype_in="continuous",
                start=start_time,
                end=end_time,
                schema="ohlcv-1m"
            ).to_df()

            if not df.empty:
                print(f"✅ {hours_back}h ago: {len(df)} bars available")
                break
            else:
                print(f"❌ {hours_back}h ago: No data")
        except Exception as e:
            print(f"❌ {hours_back}h ago: Error - {str(e)[:50]}...")

    # Recommendations
    print("\n💡 Recommendations:")
    print("1. Try NQU5 (September) or NQZ5 (December) instead of NQM5")
    print("2. Check if data has a lag (try requesting data from 1+ hours ago)")
    print("3. Use continuous contract symbol 'NQ.c.0' for front month")
    print("4. Verify the dataset supports real-time data vs delayed")

if __name__ == "__main__":
    diagnose_market_data()
