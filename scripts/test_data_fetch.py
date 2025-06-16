#!/usr/bin/env python3
"""
Test data fetching to debug chart issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from databento_5m_provider import Databento5MinuteProvider
from datetime import datetime
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_data_fetch():
    """Test basic data fetching"""
    print("=" * 60)
    print("Testing Data Fetch for Dashboard")
    print("=" * 60)

    try:
        # Initialize provider
        print("\n1. Initializing data provider...")
        provider = Databento5MinuteProvider(enable_ifd_signals=False)
        print("✅ Provider initialized")

        # Try to get data
        print("\n2. Fetching 5-minute bars...")
        df = provider.get_latest_bars(symbol="NQM5", count=10)

        if df.empty:
            print("❌ No data returned - this could be why the chart is broken")
            print("   Possible reasons:")
            print("   - Markets are closed (weekend)")
            print("   - Symbol is incorrect")
            print("   - API issues")
            return None

        print(f"✅ Got {len(df)} bars")

        # Display data info
        print("\n3. Data Summary:")
        print(f"   Time range: {df.index[0]} to {df.index[-1]}")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Last price: ${df['close'].iloc[-1]:,.2f}")

        # Check data quality
        print("\n4. Data Quality Check:")
        print(f"   NaN values: {df.isna().sum().sum()}")
        print(f"   Zero volumes: {(df['volume'] == 0).sum()}")
        print(f"   Price range: ${df['low'].min():,.2f} - ${df['high'].max():,.2f}")

        # Show sample data
        print("\n5. Sample Data (last 3 bars):")
        print(df.tail(3))

        return df

    except Exception as e:
        print(f"\n❌ Error during data fetch: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_chart_data_structure():
    """Test the data structure expected by the chart"""
    print("\n" + "=" * 60)
    print("Testing Chart Data Structure")
    print("=" * 60)

    df = test_data_fetch()

    if df is not None:
        print("\n6. Checking data types for Plotly:")
        print(f"   Index type: {type(df.index)}")
        print(f"   Index dtype: {df.index.dtype}")
        print(f"   Open dtype: {df['open'].dtype}")
        print(f"   High dtype: {df['high'].dtype}")
        print(f"   Low dtype: {df['low'].dtype}")
        print(f"   Close dtype: {df['close'].dtype}")
        print(f"   Volume dtype: {df['volume'].dtype}")

        # Check for any infinity values
        print("\n7. Checking for infinity values:")
        for col in ['open', 'high', 'low', 'close', 'volume']:
            inf_count = df[col].isin([float('inf'), float('-inf')]).sum()
            if inf_count > 0:
                print(f"   ❌ {col} has {inf_count} infinity values!")
            else:
                print(f"   ✅ {col} has no infinity values")

if __name__ == "__main__":
    test_chart_data_structure()
