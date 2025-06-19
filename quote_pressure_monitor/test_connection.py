#!/usr/bin/env python3
"""
Quick test to verify NQ options quote pressure connection works
This validates our key insight before running the full monitor
"""

import databento as db
import time
from datetime import datetime

API_KEY = os.getenv('DATABENTO_API_KEY')

symbol_count = 0
quote_count = 0

def test_callback(record):
    global symbol_count, quote_count

    record_type = type(record).__name__

    if record_type == 'SymbolMappingMsg':
        if hasattr(record, 'stype_out_symbol'):
            symbol = str(record.stype_out_symbol)
            if 'NQ' in symbol and ('C' in symbol or 'P' in symbol):
                symbol_count += 1
                if symbol_count <= 5:
                    print(f"✅ NQ Option: {symbol}")

    elif record_type == 'MbpMsg':
        quote_count += 1
        if quote_count <= 3:
            bid_size = getattr(record, 'bid_sz_00', 0)
            ask_size = getattr(record, 'ask_sz_00', 0)
            print(f"📊 Quote: Bid:{bid_size} Ask:{ask_size}")

print("🧪 TESTING NQ OPTIONS QUOTE PRESSURE CONNECTION")
print("=" * 50)

try:
    client = db.Live(key=API_KEY)

    client.subscribe(
        dataset="GLBX.MDP3",
        schema="mbp-1",  # Market By Price for quotes
        symbols=["NQ.OPT"],
        stype_in="parent",
        start=0,
    )

    client.add_callback(test_callback)
    client.start()

    print("🚀 Testing for 20 seconds...")
    time.sleep(20)

    client.stop()

    print(f"\n📊 TEST RESULTS:")
    print(f"   NQ option symbols: {symbol_count}")
    print(f"   Quote records: {quote_count}")

    if symbol_count > 0 and quote_count > 0:
        print(f"\n✅ SUCCESS! Ready for quote pressure monitoring")
    elif symbol_count > 0:
        print(f"\n⚠️  Symbols working, but no quotes (market closed?)")
    else:
        print(f"\n❌ No data - check connection/subscription")

except Exception as e:
    print(f"❌ Test failed: {e}")

print(f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
