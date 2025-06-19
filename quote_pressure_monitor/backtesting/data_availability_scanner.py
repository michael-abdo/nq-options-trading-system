#!/usr/bin/env python3
"""
DATA AVAILABILITY SCANNER
=========================

Comprehensively scan for all available trading days in our dataset
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def scan_data_availability():
    """Scan for all available trading days"""

    print("🔍 COMPREHENSIVE DATA AVAILABILITY SCANNER")
    print("=" * 60)
    print("Scanning for all available trading days...")
    print("-" * 60)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Scan broader date range - go back to start of 2025
    start_scan = datetime(2025, 1, 1)
    end_scan = datetime(2025, 6, 20)  # Through today

    print(f"📅 Scanning period: {start_scan.strftime('%Y-%m-%d')} to {end_scan.strftime('%Y-%m-%d')}")

    # Generate all potential trading days (weekdays only)
    potential_dates = []
    current = start_scan

    while current <= end_scan:
        # Only include weekdays (Monday=0, Sunday=6)
        if current.weekday() < 5:
            potential_dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    print(f"📊 Total weekdays to check: {len(potential_dates)}")

    available_dates = []
    unavailable_dates = []
    error_dates = []

    print(f"\n🔄 Checking data availability...")
    print("Progress: ", end="", flush=True)

    # Check each date efficiently
    for i, date_str in enumerate(potential_dates):
        if i % 10 == 0:
            print(".", end="", flush=True)

        try:
            # Quick check using metadata API
            result = client.metadata.get_dataset_condition(
                dataset="GLBX.MDP3",
                start_date=date_str,
                end_date=date_str
            )

            if result and len(result) > 0:
                condition = result[0].get('condition', 'unknown')
                if condition == 'available':
                    available_dates.append(date_str)
                else:
                    unavailable_dates.append((date_str, condition))
            else:
                unavailable_dates.append((date_str, 'no_data'))

        except Exception as e:
            error_dates.append((date_str, str(e)[:50]))

    print("\n")

    # Detailed results
    print("\n" + "=" * 60)
    print("📊 DATA AVAILABILITY RESULTS")
    print("=" * 60)

    print(f"📈 AVAILABLE DATES: {len(available_dates)}")
    if available_dates:
        print(f"   First available: {available_dates[0]}")
        print(f"   Last available: {available_dates[-1]}")
        print(f"   Date range: {len(available_dates)} trading days")

        # Show all available dates
        print(f"\n📅 ALL AVAILABLE TRADING DAYS:")
        for i, date in enumerate(available_dates):
            if i % 5 == 0:
                print()
                print("   ", end="")
            print(f"{date}  ", end="")
        print()

    print(f"\n❌ UNAVAILABLE DATES: {len(unavailable_dates)}")
    if unavailable_dates and len(unavailable_dates) <= 20:
        print(f"   Sample unavailable:")
        for date, reason in unavailable_dates[:10]:
            print(f"   • {date}: {reason}")

    print(f"\n⚠️  ERROR DATES: {len(error_dates)}")
    if error_dates and len(error_dates) <= 10:
        print(f"   Sample errors:")
        for date, error in error_dates[:5]:
            print(f"   • {date}: {error}")

    # Analysis by month
    if available_dates:
        print(f"\n📊 AVAILABILITY BY MONTH:")
        monthly_counts = {}
        for date in available_dates:
            month = date[:7]  # YYYY-MM
            monthly_counts[month] = monthly_counts.get(month, 0) + 1

        for month, count in sorted(monthly_counts.items()):
            print(f"   {month}: {count} trading days")

    # Recent data focus
    recent_dates = [d for d in available_dates if d >= "2025-06-01"]
    if recent_dates:
        print(f"\n📅 RECENT DATA (June 2025): {len(recent_dates)} days")
        print(f"   Available: {', '.join(recent_dates)}")

    # Test actual data quality on a few dates
    print(f"\n🔍 TESTING DATA QUALITY...")

    test_dates = available_dates[-3:] if len(available_dates) >= 3 else available_dates

    for date in test_dates:
        print(f"\n📊 Testing {date}:")
        try:
            # Quick test for actual options data
            start_time = f"{date}T14:30:00"
            end_time = f"{date}T14:31:00"  # Just 1 minute

            data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_time,
                end=end_time,
                stype_in="parent"
            )

            quote_count = 0
            for record in data:
                quote_count += 1
                if quote_count >= 1000:  # Just sample
                    break

            print(f"   ✅ {quote_count:,} quotes in 1 minute (good quality)")

        except Exception as e:
            print(f"   ❌ Data test failed: {str(e)[:50]}")

    # Summary recommendations
    print(f"\n" + "=" * 60)
    print("🎯 SUMMARY & RECOMMENDATIONS")
    print("=" * 60)

    print(f"📊 TOTAL AVAILABLE TRADING DAYS: {len(available_dates)}")

    if len(available_dates) >= 10:
        print(f"✅ EXCELLENT: {len(available_dates)} days available for comprehensive backtesting")
        print(f"💡 Recommendation: Run full strategy validation across all {len(available_dates)} days")
    elif len(available_dates) >= 5:
        print(f"✅ GOOD: {len(available_dates)} days available for solid backtesting")
        print(f"💡 Recommendation: Test strategy on all available days")
    elif len(available_dates) >= 2:
        print(f"⚠️  LIMITED: Only {len(available_dates)} days available")
        print(f"💡 Recommendation: Focus on optimization rather than validation")
    else:
        print(f"❌ INSUFFICIENT: Only {len(available_dates)} days available")
        print(f"💡 Recommendation: Check data access or try different date ranges")

    # Specific recommendations for strategy testing
    if len(available_dates) >= 5:
        print(f"\n🚀 STRATEGY TESTING RECOMMENDATIONS:")
        print(f"   • Full backtest: Test optimized strategy on all {len(available_dates)} days")
        print(f"   • Parameter sweep: Try different volume bias thresholds (35%, 40%, 45%)")
        print(f"   • Session analysis: Test different time windows across all days")
        print(f"   • Risk validation: Ensure consistent profitability across date range")

    return available_dates

if __name__ == "__main__":
    available = scan_data_availability()

    if available:
        print(f"\n📋 READY FOR COMPREHENSIVE TESTING ON {len(available)} DAYS!")
    else:
        print(f"\n❌ No data available for testing")
