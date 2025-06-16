#!/usr/bin/env python3
"""
Check data latency - why is the chart 20 minutes behind?
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'utils'))

from datetime import datetime
import pytz
from databento_5m_provider import Databento5MinuteProvider
from timezone_utils import get_eastern_time, get_utc_time

def check_data_latency():
    print("="*60)
    print("📊 DATA LATENCY CHECK")
    print("="*60)

    # Current time
    now_utc = get_utc_time()
    now_et = get_eastern_time()

    print(f"\n⏰ Current Time:")
    print(f"   UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   ET:  {now_et.strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize provider
    print("\n📊 Initializing data provider...")
    provider = Databento5MinuteProvider(enable_ifd_signals=False)

    # Get latest bars
    print("\n📈 Fetching latest 5-minute bars...")
    df = provider.get_latest_bars(symbol="NQM5", count=10)

    if df.empty:
        print("❌ No data returned!")
        return

    # Check the most recent bar
    latest_bar_time = df.index[-1]
    latest_bar_et = latest_bar_time.astimezone(pytz.timezone('US/Eastern'))

    # Calculate delay
    delay_seconds = (now_utc - latest_bar_time).total_seconds()
    delay_minutes = delay_seconds / 60

    print(f"\n📊 Latest Bar Analysis:")
    print(f"   Time (UTC): {latest_bar_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Time (ET):  {latest_bar_et.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Close Price: ${df['close'].iloc[-1]:,.2f}")
    print(f"   Volume: {df['volume'].iloc[-1]:,}")

    print(f"\n⏱️  Data Delay:")
    print(f"   {delay_minutes:.1f} minutes behind current time")

    if delay_minutes > 15:
        print(f"   ⚠️  WARNING: Data is {delay_minutes:.0f} minutes old!")
    elif delay_minutes > 10:
        print(f"   ⚠️  Data is somewhat delayed")
    else:
        print(f"   ✅ Data is reasonably current")

    # Show last 5 bars
    print(f"\n📊 Last 5 bars:")
    for i in range(max(0, len(df)-5), len(df)):
        bar_time = df.index[i]
        bar_et = bar_time.astimezone(pytz.timezone('US/Eastern'))
        print(f"   {bar_et.strftime('%H:%M ET')}: ${df['close'].iloc[i]:,.2f} (vol: {df['volume'].iloc[i]:,})")

    # Check live buffer
    print(f"\n🔴 Live Data Buffer:")
    print(f"   Buffer size: {len(provider._live_data_buffer)} bars")
    if provider._live_data_buffer:
        latest_live = provider._live_data_buffer[-1]
        print(f"   Latest live bar: {latest_live['timestamp']}")

if __name__ == "__main__":
    check_data_latency()
