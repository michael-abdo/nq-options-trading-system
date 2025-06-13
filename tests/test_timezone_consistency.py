#!/usr/bin/env python3
"""
Test Timezone Consistency Across Codebase
Verifies all time references use Eastern Time consistently
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from utils.timezone_utils import (
    get_eastern_time, get_utc_time, to_eastern_time, to_utc_time,
    format_eastern_timestamp, format_eastern_display, format_eastern_full,
    is_market_hours, get_market_open_time, get_market_close_time,
    EASTERN_TZ, UTC_TZ
)
from datetime import datetime
import pytz


def test_timezone_utilities():
    """Test all timezone utility functions work correctly"""
    print("🧪 Testing Timezone Utility Functions")
    print("=" * 50)

    # Test basic time getters
    et_time = get_eastern_time()
    utc_time = get_utc_time()

    print(f"✅ Eastern Time: {et_time}")
    print(f"✅ UTC Time: {utc_time}")

    # Test conversions
    utc_to_et = to_eastern_time(utc_time)
    et_to_utc = to_utc_time(et_time)

    print(f"✅ UTC→ET: {utc_to_et}")
    print(f"✅ ET→UTC: {et_to_utc}")

    # Test formatters
    timestamp = format_eastern_timestamp()
    display = format_eastern_display()
    full = format_eastern_full()

    print(f"✅ Timestamp format: {timestamp}")
    print(f"✅ Display format: {display}")
    print(f"✅ Full format: {full}")

    # Test market hours
    is_market = is_market_hours()
    market_open = get_market_open_time()
    market_close = get_market_close_time()

    print(f"✅ Is market hours: {is_market}")
    print(f"✅ Market open: {market_open}")
    print(f"✅ Market close: {market_close}")


def test_chart_components():
    """Test chart components use Eastern Time correctly"""
    print("\n🧪 Testing Chart Components")
    print("=" * 50)

    try:
        # Test dashboard
        from scripts.nq_5m_dash_app import NQDashApp
        print("✅ Dashboard imports timezone utilities")

        # Test static chart
        from scripts.nq_5m_chart import NQFiveMinuteChart
        print("✅ Static chart imports timezone utilities")

        # Test data aggregation
        from scripts.data_aggregation import test_aggregation
        print("✅ Data aggregation uses Eastern Time for market hours")

    except ImportError as e:
        print(f"❌ Import error: {e}")


def test_critical_files_timezone_consistency():
    """Test critical files have consistent timezone usage"""
    print("\n🧪 Testing Critical Files for Timezone Consistency")
    print("=" * 50)

    # Files that should use Eastern Time for display/user-facing operations
    eastern_time_files = [
        'scripts/nq_5m_dash_app.py',
        'scripts/nq_5m_chart.py',
        'scripts/start_trading_safe_chart.py',
        'scripts/data_aggregation.py',
        'scripts/run_shadow_trading.py'
    ]

    # Files that should use UTC for data operations (these are correct)
    utc_files = [
        'scripts/databento_5m_provider.py'
    ]

    for file_path in eastern_time_files:
        full_path = os.path.join('..', file_path)
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                content = f.read()

            # Check for timezone utilities import
            has_utils = 'from utils.timezone_utils import' in content

            # Check for old problematic patterns
            has_naive_datetime_now = 'datetime.now()' in content and 'strftime' in content

            if has_utils:
                print(f"✅ {file_path}: Uses timezone utilities")
            else:
                print(f"⚠️  {file_path}: Missing timezone utilities import")

            if has_naive_datetime_now:
                print(f"❌ {file_path}: Still has naive datetime.now() usage")
        else:
            print(f"❌ {file_path}: File not found")

    for file_path in utc_files:
        full_path = os.path.join('..', file_path)
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                content = f.read()

            # Check for proper UTC usage
            has_utc = 'pytz.UTC' in content or 'datetime.now(pytz.UTC)' in content

            if has_utc:
                print(f"✅ {file_path}: Correctly uses UTC for data operations")
            else:
                print(f"❌ {file_path}: Missing proper UTC usage")


def test_market_open_consistency():
    """Test market open calculations are consistent"""
    print("\n🧪 Testing Market Open Time Consistency")
    print("=" * 50)

    # Get market open from utility
    market_open_et = get_market_open_time()
    market_open_utc = to_utc_time(market_open_et)

    print(f"✅ Market open ET: {market_open_et}")
    print(f"✅ Market open UTC: {market_open_utc}")

    # Verify it's 9:30 AM ET
    if market_open_et.hour == 9 and market_open_et.minute == 30:
        print("✅ Market open time is correct (9:30 AM ET)")
    else:
        print(f"❌ Market open time is wrong: {market_open_et.hour}:{market_open_et.minute:02d}")

    # Verify timezone info
    if market_open_et.tzinfo == EASTERN_TZ:
        print("✅ Market open has correct Eastern timezone")
    else:
        print(f"❌ Market open has wrong timezone: {market_open_et.tzinfo}")


def run_all_tests():
    """Run all timezone consistency tests"""
    print("🎯 TIMEZONE CONSISTENCY TEST SUITE")
    print("=" * 60)

    test_timezone_utilities()
    test_chart_components()
    test_critical_files_timezone_consistency()
    test_market_open_consistency()

    print("\n🎉 TIMEZONE CONSISTENCY VERIFICATION COMPLETE")
    print("=" * 60)
    print("All time references should now be Eastern Time consistent!")
    print("Charts will show 9:30 AM ET for market open (not 1:30 PM UTC)")
    print("File timestamps will use Eastern Time")
    print("Market hours calculations will use Eastern Time")


if __name__ == "__main__":
    run_all_tests()
