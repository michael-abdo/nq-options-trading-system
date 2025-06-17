#!/usr/bin/env python3
"""
Live Quotes Demo - Shows NQ bid/ask updates
Quotes update much more frequently than trades
"""

import databento as db
import os
import time
from datetime import datetime

def main():
    print("📊 DATABENTO LIVE NQ QUOTES")
    print("="*50)

    client = db.Live(key=os.getenv('DATABENTO_API_KEY'))

    quote_count = 0
    last_bid = None
    last_ask = None

    def on_data(record):
        nonlocal quote_count, last_bid, last_ask

        # Handle quote records (MBP = Market By Price)
        if hasattr(record, 'bid_px_00') and hasattr(record, 'ask_px_00'):
            if record.bid_px_00 and record.ask_px_00:
                quote_count += 1

                bid = float(record.bid_px_00) / 1e9
                ask = float(record.ask_px_00) / 1e9
                spread = ask - bid
                mid = (bid + ask) / 2

                # Show every 10th quote to avoid spam
                if quote_count % 10 == 1:
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]

                    # Show changes
                    bid_change = f" ({bid - last_bid:+.2f})" if last_bid else ""
                    ask_change = f" ({ask - last_ask:+.2f})" if last_ask else ""

                    print(f"[{timestamp}] Quote #{quote_count}")
                    print(f"  Bid: ${bid:,.2f}{bid_change}")
                    print(f"  Ask: ${ask:,.2f}{ask_change}")
                    print(f"  Mid: ${mid:,.2f} | Spread: ${spread:.2f}")
                    print()

                    last_bid = bid
                    last_ask = ask

    client.add_callback(on_data)

    # Subscribe to top of book (best bid/ask)
    print("Subscribing to NQ top of book...")
    client.subscribe(
        dataset='GLBX.MDP3',
        symbols=['NQ.c.0'],
        schema='mbp-1'  # Market By Price, 1 level (top of book)
    )

    print("Starting stream...")
    client.start()

    print("Streaming for 20 seconds...\n")

    start_time = time.time()
    while time.time() - start_time < 20:
        time.sleep(0.1)

        # Show progress
        if quote_count > 0 and quote_count % 100 == 0:
            elapsed = int(time.time() - start_time)
            rate = quote_count / elapsed if elapsed > 0 else 0
            print(f"⚡ {quote_count} quotes in {elapsed}s ({rate:.1f}/sec)\n")

    print(f"\n📊 Total quotes received: {quote_count}")
    print(f"Rate: {quote_count/20:.1f} quotes/second")

    client.stop()
    print("\nDone!")

if __name__ == "__main__":
    main()
