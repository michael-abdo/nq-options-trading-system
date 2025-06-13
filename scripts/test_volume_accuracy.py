#!/usr/bin/env python3
"""
Test volume accuracy in 5-minute aggregation
Compare raw 1-minute volumes vs aggregated 5-minute volumes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from databento_5m_provider import Databento5MinuteProvider
from databento_auth import ensure_trading_safe_databento_client
import pandas as pd
from datetime import datetime, timedelta

def test_volume_accuracy():
    """Test volume aggregation accuracy"""
    print("🧪 Testing Volume Accuracy in 5-Minute Aggregation")
    print("=" * 60)

    try:
        # Get authenticated client for raw data
        client = ensure_trading_safe_databento_client()

        # Get 1 hour of data for detailed analysis
        end = datetime.now()
        start = end - timedelta(hours=1)

        print(f"\n📊 Fetching raw 1-minute data...")
        print(f"Time range: {start} to {end}")

        # Fetch raw 1-minute data
        data = client.timeseries.get_range(
            dataset="GLBX.MDP3",
            symbols=["NQM5"],
            schema="ohlcv-1m",
            start=start,
            end=end
        )

        df_1min = data.to_df()

        if df_1min.empty:
            print("❌ No raw data available")
            return

        print(f"✅ Retrieved {len(df_1min)} raw 1-minute bars")

        # Show sample raw volumes
        print(f"\n📈 Sample 1-minute volumes:")
        for i in range(min(10, len(df_1min))):
            timestamp = df_1min.index[i]
            volume = df_1min.iloc[i]['volume']
            print(f"  {timestamp}: {volume:,}")

        # Calculate total 1-minute volume
        total_1min_volume = df_1min['volume'].sum()
        print(f"\n📊 Total 1-minute volume: {total_1min_volume:,}")

        # Now get 5-minute aggregated data
        print(f"\n📊 Testing 5-minute aggregation...")
        provider = Databento5MinuteProvider()
        df_5min = provider.get_historical_5min_bars(
            symbol="NQM5",
            start=start,
            end=end
        )

        if df_5min.empty:
            print("❌ No 5-minute data available")
            return

        print(f"✅ Retrieved {len(df_5min)} 5-minute bars")

        # Show sample 5-minute volumes
        print(f"\n📈 Sample 5-minute volumes:")
        for i in range(min(5, len(df_5min))):
            timestamp = df_5min.index[i]
            volume = df_5min.iloc[i]['volume']
            print(f"  {timestamp}: {volume:,}")

        # Calculate total 5-minute volume
        total_5min_volume = df_5min['volume'].sum()
        print(f"\n📊 Total 5-minute volume: {total_5min_volume:,}")

        # Compare volumes
        volume_diff = abs(total_1min_volume - total_5min_volume)
        volume_diff_pct = (volume_diff / total_1min_volume * 100) if total_1min_volume > 0 else 0

        print(f"\n🔍 Volume Comparison:")
        print(f"  1-minute total: {total_1min_volume:,}")
        print(f"  5-minute total: {total_5min_volume:,}")
        print(f"  Difference: {volume_diff:,} ({volume_diff_pct:.2f}%)")

        if volume_diff_pct < 1:
            print("✅ Volume aggregation is ACCURATE")
        else:
            print("❌ Volume aggregation has DISCREPANCY")

        # Detailed analysis - check specific 5-minute periods
        print(f"\n🔍 Detailed 5-minute period analysis:")
        print("-" * 50)

        # Group 1-minute data by 5-minute periods
        df_1min_resampled = df_1min.resample('5min').agg({
            'volume': 'sum',
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()

        # Compare first few periods
        for i in range(min(3, len(df_5min), len(df_1min_resampled))):
            ts_5min = df_5min.index[i]
            ts_1min = df_1min_resampled.index[i]
            vol_5min = df_5min.iloc[i]['volume']
            vol_1min = df_1min_resampled.iloc[i]['volume']

            print(f"Period {i+1}:")
            print(f"  Timestamp: {ts_5min}")
            print(f"  5min volume: {vol_5min:,}")
            print(f"  1min agg volume: {vol_1min:,}")
            print(f"  Match: {'✅' if vol_5min == vol_1min else '❌'}")
            print()

        # Check for any data quality issues
        print(f"🔍 Data Quality Checks:")
        print(f"  1-min bars with zero volume: {(df_1min['volume'] == 0).sum()}")
        print(f"  5-min bars with zero volume: {(df_5min['volume'] == 0).sum()}")
        print(f"  1-min average volume: {df_1min['volume'].mean():,.0f}")
        print(f"  5-min average volume: {df_5min['volume'].mean():,.0f}")
        print(f"  Expected 5-min avg (5x 1-min): {df_1min['volume'].mean() * 5:,.0f}")

        # Check time alignment
        print(f"\n⏰ Time Alignment Check:")
        print(f"  1-min first bar: {df_1min.index[0]}")
        print(f"  1-min last bar: {df_1min.index[-1]}")
        print(f"  5-min first bar: {df_5min.index[0]}")
        print(f"  5-min last bar: {df_5min.index[-1]}")

    except Exception as e:
        print(f"❌ Error testing volume accuracy: {e}")

if __name__ == "__main__":
    test_volume_accuracy()
