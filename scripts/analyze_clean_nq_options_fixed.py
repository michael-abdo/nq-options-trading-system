#!/usr/bin/env python3
"""
Fixed analysis of NQ options with proper pandas handling
"""

import os
import databento as db
from datetime import datetime, timezone
import pandas as pd
import re

def analyze_clean_nq_options():
    """Analyze only actual NQ option symbols with fixed pandas warnings"""
    print("=" * 60)
    print("CLEAN NQ OPTIONS ANALYSIS (FIXED)")
    print("=" * 60)

    try:
        # Initialize client
        api_key = os.getenv('DATABENTO_API_KEY')
        if not api_key:
            print("❌ DATABENTO_API_KEY environment variable not set")
            return
        client = db.Historical(api_key)

        # Get today's data
        end_time = datetime(2025, 6, 16, 14, 10, tzinfo=timezone.utc)
        start_time = datetime(2025, 6, 16, 12, 0, tzinfo=timezone.utc)

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
            print(f"✅ Retrieved {len(df)} total trades")

            # Filter for actual NQ options (format: NQM5 C/P followed by strike)
            nq_pattern = r'^NQ[A-Z]\d+ [CP]\d+$'
            nq_options = df[df['symbol'].str.match(nq_pattern, na=False)].copy()  # Use .copy() to avoid warning

            print(f"📊 Actual NQ options: {len(nq_options)} trades")
            print(f"📊 Other symbols: {len(df) - len(nq_options)} trades")

            if len(nq_options) > 0:
                # Analyze actual NQ options
                calls = nq_options[nq_options['symbol'].str.contains(' C', na=False)].copy()
                puts = nq_options[nq_options['symbol'].str.contains(' P', na=False)].copy()

                call_volume = calls['size'].sum()
                put_volume = puts['size'].sum()

                print(f"\n🎯 TODAY'S NQ OPTIONS FLOW (VERIFIED):")
                print(f"   Time Range: 8:00 AM - 10:09 AM ET")
                print(f"   Total NQ Option Trades: {len(nq_options)}")
                print(f"   Call Trades: {len(calls)} (Volume: {call_volume:,})")
                print(f"   Put Trades: {len(puts)} (Volume: {put_volume:,})")

                if call_volume > 0:
                    pc_ratio = put_volume / call_volume
                    print(f"   Put/Call Volume Ratio: {pc_ratio:.3f}")

                    # Market sentiment
                    if pc_ratio < 0.7:
                        sentiment = "BULLISH"
                    elif pc_ratio < 1.3:
                        sentiment = "NEUTRAL"
                    else:
                        sentiment = "BEARISH"

                    print(f"   Market Sentiment: {sentiment}")

                # Show actual NQ trades
                print(f"\n📈 Recent NQ Option Trades:")
                print("-" * 50)
                recent_nq = nq_options.tail(10)
                for idx, row in recent_nq.iterrows():
                    et_time = idx.tz_convert('US/Eastern')
                    symbol = row['symbol']
                    price = row['price']
                    size = row['size']
                    print(f"   {et_time.strftime('%H:%M:%S ET')} | {symbol}: ${price:.2f} x {size}")

                # Strike analysis - FIXED VERSION
                print(f"\n🎯 Strike Distribution:")
                print("-" * 50)

                # Extract strikes from symbols using proper pandas approach
                def extract_strike(symbol):
                    match = re.search(r'[CP](\d+)', symbol)
                    return int(match.group(1)) if match else None

                # Use .loc to avoid SettingWithCopyWarning
                nq_options.loc[:, 'strike'] = nq_options['symbol'].apply(extract_strike)
                calls.loc[:, 'strike'] = calls['symbol'].apply(extract_strike)
                puts.loc[:, 'strike'] = puts['symbol'].apply(extract_strike)

                # Remove any rows where strike extraction failed
                nq_options = nq_options.dropna(subset=['strike'])
                calls = calls.dropna(subset=['strike'])
                puts = puts.dropna(subset=['strike'])

                if len(calls) > 0:
                    # Call strikes
                    call_strikes = calls['strike'].value_counts().sort_index()
                    print("   Most Active Call Strikes:")
                    for strike, count in call_strikes.head(5).items():
                        print(f"     {int(strike)}: {count} trades")

                if len(puts) > 0:
                    # Put strikes
                    put_strikes = puts['strike'].value_counts().sort_index()
                    print("   Most Active Put Strikes:")
                    for strike, count in put_strikes.head(5).items():
                        print(f"     {int(strike)}: {count} trades")

                # Additional analysis: Premium weighted strikes
                if len(nq_options) > 0:
                    nq_options.loc[:, 'premium'] = nq_options['price'] * nq_options['size'] * 100

                    print(f"\n💰 Premium-Weighted Analysis:")
                    print("-" * 50)

                    strike_premium = nq_options.groupby('strike')['premium'].sum().sort_values(ascending=False)
                    print("   Top Strikes by Premium Flow:")
                    for strike, premium in strike_premium.head(5).items():
                        option_type = 'MIXED'
                        strike_data = nq_options[nq_options['strike'] == strike]
                        if len(strike_data) > 0:
                            if all('C' in sym for sym in strike_data['symbol']):
                                option_type = 'CALLS'
                            elif all('P' in sym for sym in strike_data['symbol']):
                                option_type = 'PUTS'
                        print(f"     {int(strike)} ({option_type}): ${premium:,.0f}")

            else:
                print("❌ No actual NQ option trades found")

            # Show what other symbols were included
            other_symbols = df[~df['symbol'].str.match(nq_pattern, na=False)]['symbol'].unique()
            if len(other_symbols) > 0:
                print(f"\n🔍 Other symbols in NQ.OPT query:")
                for symbol in other_symbols[:10]:  # Show first 10
                    print(f"   {symbol}")
                if len(other_symbols) > 10:
                    print(f"   ... and {len(other_symbols) - 10} more")

        else:
            print("❌ No data retrieved")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_clean_nq_options()
