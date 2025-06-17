#!/usr/bin/env python3
"""
Ultimate Databento Test - Will show ANY data if available
"""

import databento as db
import os
import time
from datetime import datetime

def main():
    print("🚀 ULTIMATE DATABENTO TEST")
    print("="*50)

    client = db.Live(key=os.getenv('DATABENTO_API_KEY'))

    total_records = 0
    symbol_counts = {}

    def on_data(record):
        nonlocal total_records
        total_records += 1

        # Track what we're getting
        record_type = type(record).__name__

        # Get symbol if available
        symbol = getattr(record, 'symbol', 'UNKNOWN')
        if symbol not in symbol_counts:
            symbol_counts[symbol] = 0
        symbol_counts[symbol] += 1

        # First few records - show everything
        if total_records <= 5:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Record #{total_records}")
            print(f"  Type: {record_type}")
            print(f"  Symbol: {symbol}")

            # Show all attributes
            attrs = [a for a in dir(record) if not a.startswith('_')]
            print(f"  Attributes: {attrs[:10]}...")

            # Show key data
            if hasattr(record, 'price'):
                print(f"  Price: {float(record.price)/1e9:.2f}")
            if hasattr(record, 'size'):
                print(f"  Size: {record.size}")
            if hasattr(record, 'msg'):
                print(f"  Message: {record.msg}")

        # After 5, just count
        elif total_records % 100 == 0:
            print(f"\n⚡ {total_records} records received!")
            print(f"  Symbols seen: {list(symbol_counts.keys())[:5]}")

    client.add_callback(on_data)

    # Try EVERYTHING
    print("\n1️⃣ Subscribing to ALL CME symbols...")
    try:
        client.subscribe(
            dataset='GLBX.MDP3',
            symbols=['ALL_SYMBOLS'],
            schema='mbp-1'
        )
        print("✅ Subscribed to ALL_SYMBOLS")
    except Exception as e:
        print(f"❌ ALL_SYMBOLS failed: {e}")

        # Fallback to specific symbols
        print("\n2️⃣ Trying specific symbols...")
        for symbol in ['NQ.c.0', 'ES.c.0', 'GC.c.0', 'CL.c.0']:
            try:
                client.subscribe(
                    dataset='GLBX.MDP3',
                    symbols=[symbol],
                    schema='mbp-1'
                )
                print(f"✅ Subscribed to {symbol}")
            except Exception as e:
                print(f"❌ {symbol} failed: {e}")

    print("\n3️⃣ Starting stream...")
    client.start()

    print("⏳ Waiting for ANY data (60 seconds)...")
    print("   If market is open, data should appear within seconds")
    print("   Press Ctrl+C to stop early\n")

    start_time = time.time()

    try:
        while time.time() - start_time < 60:
            time.sleep(1)

            # Status every 10 seconds
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                if total_records == 0:
                    print(f"[{elapsed}s] Still waiting for data...")
                else:
                    rate = total_records / elapsed
                    print(f"[{elapsed}s] Total: {total_records} records ({rate:.1f}/sec)")

    except KeyboardInterrupt:
        print("\n\nStopped by user")

    # Final report
    print(f"\n📊 FINAL REPORT")
    print(f"="*50)
    print(f"Total records: {total_records}")

    if total_records > 0:
        print(f"\nSymbols received:")
        for symbol, count in sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {symbol}: {count} records")
        print("\n✅ DATA IS FLOWING!")
    else:
        print("\n❌ NO DATA RECEIVED")
        print("\nPossible reasons:")
        print("  1. Market might be in a quiet period")
        print("  2. Connection/firewall issues")
        print("  3. Subscription permissions")
        print("\nTry running during active market hours (9:30 AM - 4:00 PM ET)")

    client.stop()

if __name__ == "__main__":
    main()
