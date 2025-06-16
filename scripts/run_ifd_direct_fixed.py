#!/usr/bin/env python3
"""
Fixed IFD analysis with proper pandas handling
"""

import os
import sys
sys.path.append('/Users/Mike/trading/algos/EOD')
sys.path.append('/Users/Mike/trading/algos/EOD/tasks/options_trading_system')

import databento as db
from datetime import datetime, timezone
import pandas as pd
import json

def run_ifd_analysis():
    """Run IFD analysis on today's option data with fixed pandas handling"""
    print("=" * 60)
    print("DIRECT IFD ANALYSIS - LIVE CHECK (FIXED)")
    print("=" * 60)

    try:
        # Get the verified data from today
        api_key = os.getenv('DATABENTO_API_KEY')
        if not api_key:
            print("❌ DATABENTO_API_KEY environment variable not set")
            return
        client = db.Historical(api_key)

        # Get most recent data (up to 10:10 AM ET)
        end_time = datetime(2025, 6, 16, 14, 10, tzinfo=timezone.utc)
        start_time = datetime(2025, 6, 16, 13, 30, tzinfo=timezone.utc)  # Last 40 minutes

        print(f"\n📊 Analyzing last 40 minutes: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} UTC")
        print(f"   (9:30 AM - 10:10 AM ET)")

        # Get options data
        options_data = client.timeseries.get_range(
            dataset='GLBX.MDP3',
            symbols=['NQ.OPT'],
            start=start_time,
            end=end_time,
            schema='trades',
            stype_in='parent'
        )

        df = options_data.to_df()

        if not df.empty:
            # Filter for actual NQ options - FIXED VERSION
            import re
            nq_pattern = r'^NQ[A-Z]\d+ [CP]\d+$'
            nq_options = df[df['symbol'].str.match(nq_pattern, na=False)].copy()  # Use .copy() to avoid warning

            print(f"✅ Found {len(nq_options)} NQ option trades in recent period")

            if len(nq_options) > 0:
                # IFD Analysis - Look for institutional characteristics
                print(f"\n🔍 IFD INSTITUTIONAL FLOW ANALYSIS:")
                print("-" * 50)

                # 1. Large block analysis (institutional threshold: >50 contracts)
                large_blocks = nq_options[nq_options['size'] >= 50]
                print(f"   Large Blocks (≥50 contracts): {len(large_blocks)} trades")

                if len(large_blocks) > 0:
                    print("   🚨 INSTITUTIONAL ACTIVITY DETECTED:")
                    for idx, row in large_blocks.iterrows():
                        et_time = idx.tz_convert('US/Eastern')
                        symbol = row['symbol']
                        price = row['price']
                        size = row['size']
                        premium = price * size * 100  # Options contract multiplier
                        print(f"     {et_time.strftime('%H:%M:%S ET')} | {symbol}: ${price:.2f} x {size} (${premium:,.0f})")

                # 2. Unusual volume analysis
                volume_by_strike = nq_options.groupby('symbol')['size'].sum().sort_values(ascending=False)
                high_volume_strikes = volume_by_strike[volume_by_strike >= 20]  # 20+ total volume

                print(f"\n   High Volume Strikes (≥20 total): {len(high_volume_strikes)}")
                if len(high_volume_strikes) > 0:
                    print("   🎯 CONCENTRATED ACTIVITY:")
                    for symbol, volume in high_volume_strikes.head(5).items():
                        print(f"     {symbol}: {volume} total contracts")

                # 3. Premium flow analysis - FIXED VERSION
                nq_options.loc[:, 'premium'] = nq_options['price'] * nq_options['size'] * 100  # Use .loc to avoid warning
                total_premium = nq_options['premium'].sum()

                # Separate calls and puts
                calls = nq_options[nq_options['symbol'].str.contains(' C', na=False)].copy()
                puts = nq_options[nq_options['symbol'].str.contains(' P', na=False)].copy()

                call_premium = calls['premium'].sum()
                put_premium = puts['premium'].sum()

                print(f"\n   Premium Flow Analysis:")
                print(f"     Total Premium: ${total_premium:,.0f}")
                print(f"     Call Premium: ${call_premium:,.0f}")
                print(f"     Put Premium: ${put_premium:,.0f}")

                if call_premium > 0:
                    put_call_premium_ratio = put_premium / call_premium
                    print(f"     Put/Call Premium Ratio: {put_call_premium_ratio:.3f}")

                # 4. IFD Signal Generation
                print(f"\n🎯 IFD SIGNAL ASSESSMENT:")
                print("-" * 50)

                # Signal criteria
                has_large_blocks = len(large_blocks) > 0
                has_concentrated_volume = len(high_volume_strikes) > 0
                significant_premium = total_premium > 100000  # $100k threshold

                if has_large_blocks:
                    print("   ✅ INSTITUTIONAL BLOCK DETECTED")
                    confidence = 85 if len(large_blocks) >= 3 else 75
                    action = "STRONG_BUY" if call_premium > put_premium else "STRONG_SELL"
                    print(f"   📊 Confidence: {confidence}%")
                    print(f"   🎯 Recommended Action: {action}")
                    print(f"   🚨 IFD SIGNAL: ACTIVE")

                elif has_concentrated_volume and significant_premium:
                    print("   ⚠️  ELEVATED ACTIVITY DETECTED")
                    confidence = 70
                    action = "MONITOR"
                    print(f"   📊 Confidence: {confidence}%")
                    print(f"   🎯 Recommended Action: {action}")
                    print(f"   🔍 IFD SIGNAL: WATCH")

                else:
                    print("   ➖ NO INSTITUTIONAL FLOW DETECTED")
                    print("   📊 Activity Level: RETAIL")
                    print("   🎯 Recommended Action: HOLD")
                    print(f"   🔕 IFD SIGNAL: NONE")

                # 5. Most recent trades
                print(f"\n📈 Last 5 Option Trades:")
                print("-" * 50)
                for idx, row in nq_options.tail(5).iterrows():
                    et_time = idx.tz_convert('US/Eastern')
                    symbol = row['symbol']
                    price = row['price']
                    size = row['size']
                    premium = row['premium']
                    print(f"   {et_time.strftime('%H:%M:%S ET')} | {symbol}: ${price:.2f} x {size} (${premium:,.0f})")

            else:
                print("❌ No NQ option trades in recent period")
                print("🔕 IFD SIGNAL: NONE (No activity)")

        else:
            print("❌ No option data in recent period")
            print("🔕 IFD SIGNAL: NONE (No data)")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_ifd_analysis()
