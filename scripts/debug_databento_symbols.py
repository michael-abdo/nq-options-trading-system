#!/usr/bin/env python3
"""
Debug Databento symbols and schemas
"""

import databento as db
import os
from datetime import datetime, timedelta
import time

api_key = os.getenv('DATABENTO_API_KEY')
historical = db.Historical(key=api_key)
live = db.Live(key=api_key)

print("DATABENTO SYMBOL AND SCHEMA DEBUG")
print("="*50)
print(f"Time: {datetime.now()} PT")
print()

# Test 1: Check what symbols work with historical first
print("1. Testing historical data (to verify symbols)...")
try:
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=10)

    data = historical.timeseries.get_range(
        dataset='GLBX.MDP3',
        symbols=['NQ.c.0'],
        schema='trades',
        start=start_time,
        end=end_time
    )

    count = 0
    for record in data:
        if hasattr(record, 'price'):
            price = float(record.price) / 1e9
            print(f"  Historical NQ: ${price:.2f}")
            count += 1
            if count >= 3:
                break

    if count > 0:
        print(f"  ✅ Found {count} historical trades - symbol is correct!")
    else:
        print("  ❌ No historical trades found")

except Exception as e:
    print(f"  ❌ Historical test failed: {e}")

# Test 2: Try different schemas for live data
print("\n2. Testing live data with different schemas...")
schemas = ['trades', 'mbp-1', 'mbp-10', 'mbo', 'ohlcv-1s', 'ohlcv-1m']

for schema in schemas:
    print(f"\n  Testing schema: {schema}")
    try:
        # Create new live client for each test
        test_live = db.Live(key=api_key)

        test_live.subscribe(
            dataset='GLBX.MDP3',
            symbols=['NQ.c.0'],
            schema=schema
        )

        print(f"    Subscribed, waiting for data...")

        # Set a timeout
        start_wait = time.time()
        data_found = False

        for record in test_live:
            elapsed = time.time() - start_wait

            print(f"    Got record: {type(record).__name__}")

            # Show some fields
            if hasattr(record, 'price'):
                price = float(record.price) / 1e9
                print(f"    Price: ${price:.2f}")
            elif hasattr(record, 'bid_px_00'):
                bid = float(record.bid_px_00) / 1e9
                ask = float(record.ask_px_00) / 1e9
                print(f"    Bid/Ask: ${bid:.2f} / ${ask:.2f}")
            elif hasattr(record, 'open'):
                open_px = float(record.open) / 1e9
                print(f"    OHLCV Open: ${open_px:.2f}")

            data_found = True
            break

        if not data_found and elapsed > 5:
            print(f"    ⏱️ No data after 5 seconds")

        test_live.stop()

    except Exception as e:
        print(f"    ❌ Error: {e}")

# Test 3: Try alternate symbol formats
print("\n3. Testing alternate NQ symbol formats...")
alt_symbols = ['NQ', 'NQM5', 'NQZ5', 'NQ.FUT', '/NQ', 'NQ.n.0']

for symbol in alt_symbols:
    print(f"\n  Testing: {symbol}")
    try:
        test_live = db.Live(key=api_key)
        test_live.subscribe(
            dataset='GLBX.MDP3',
            symbols=[symbol],
            schema='trades'
        )

        # Quick check
        got_data = False
        for i, record in enumerate(test_live):
            print(f"    ✅ Got data!")
            got_data = True
            break

        if not got_data:
            print(f"    ❌ No data")

        test_live.stop()

    except Exception as e:
        print(f"    ❌ Error: {str(e)[:50]}...")

print("\n" + "="*50)
print("Debug complete!")
