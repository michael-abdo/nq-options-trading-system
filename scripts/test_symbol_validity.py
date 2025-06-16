#!/usr/bin/env python3
"""
Test Symbol Validity - WHY does live streaming close immediately?
"""

import databento as db
import sys
import os
sys.path.append('.')
from databento_auth import ensure_trading_safe_databento_client
from datetime import datetime, timedelta

def test_symbol_validity():
    print("🔍 TESTING WHY LIVE STREAMING CLOSES IMMEDIATELY")
    print("=" * 60)

    client = ensure_trading_safe_databento_client()

    # Test symbols in order of likelihood
    test_symbols = [
        'NQZ24',     # December 2024 (should be active)
        'NQH25',     # March 2025 (next active contract)
        'NQM25',     # June 2025 (our current symbol)
        'NQ.FUT',    # Continuous contract
    ]

    print("\n🧪 PHASE 1: Testing Historical Data Availability")
    print("-" * 50)

    for symbol in test_symbols:
        print(f"\n📊 Testing {symbol}:")
        try:
            end_time = datetime.now().replace(microsecond=0)
            start_time = end_time - timedelta(minutes=10)

            data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=[symbol],
                schema="ohlcv-1m",
                start=start_time,
                end=end_time
            )

            df = data.to_df()
            if not df.empty:
                last_price = df['close'].iloc[-1]
                print(f"   ✅ Historical: {len(df)} bars, last: ${last_price:,.2f}")
            else:
                print(f"   ⚠️  Historical: Symbol exists but no recent data")

        except Exception as e:
            error_msg = str(e).lower()
            if 'symbol' in error_msg or 'not found' in error_msg:
                print(f"   ❌ Invalid symbol: {symbol}")
            else:
                print(f"   ❌ Error: {e}")

    print("\n🧪 PHASE 2: Testing Live Streaming Schemas")
    print("-" * 50)

    # Use the symbol that worked best from historical test
    working_symbol = 'NQZ24'  # Most likely to be active

    test_schemas = ['ohlcv-1s', 'ohlcv-1m', 'tbbo', 'trades']

    for schema in test_schemas:
        print(f"\n📡 Testing schema {schema} with {working_symbol}:")
        try:
            live_client = db.Live(key=client._key)

            # Try subscription (don't iterate, just test acceptance)
            live_client.subscribe(
                dataset="GLBX.MDP3",
                schema=schema,
                symbols=[working_symbol],
                stype_in="continuous"
            )

            print(f"   ✅ Subscription accepted for {schema}")

            # Quick test: try to get one record
            record_count = 0
            for record in live_client:
                record_count += 1
                if record_count >= 1:  # Just test one record
                    print(f"   🎯 GOT DATA: {schema} works!")
                    break

            if record_count == 0:
                print(f"   ❌ Subscription accepted but EOF immediately")

            live_client.stop()

        except Exception as e:
            error_msg = str(e).lower()
            if 'schema' in error_msg or 'not supported' in error_msg:
                print(f"   ❌ Schema not supported: {schema}")
            elif 'symbol' in error_msg:
                print(f"   ❌ Symbol issue with {schema}")
            else:
                print(f"   ❌ Error: {e}")

    print("\n🧪 PHASE 3: Testing Symbol Types")
    print("-" * 50)

    symbol_types = ['continuous', 'raw_symbol', 'instrument_id']

    for stype in symbol_types:
        print(f"\n🎯 Testing stype_in={stype}:")
        try:
            live_client = db.Live(key=client._key)

            live_client.subscribe(
                dataset="GLBX.MDP3",
                schema="ohlcv-1s",
                symbols=[working_symbol],
                stype_in=stype
            )

            print(f"   ✅ Subscription accepted for stype={stype}")

            # Quick data test
            record_count = 0
            for record in live_client:
                record_count += 1
                if record_count >= 1:
                    print(f"   🎯 DATA FLOWING: stype={stype} works!")
                    break

            if record_count == 0:
                print(f"   ❌ EOF immediately with stype={stype}")

            live_client.stop()

        except Exception as e:
            print(f"   ❌ Error with stype={stype}: {e}")

if __name__ == "__main__":
    test_symbol_validity()
