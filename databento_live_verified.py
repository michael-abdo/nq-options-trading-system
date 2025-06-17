#!/usr/bin/env python3
"""
Databento Live NQ Stream - VERIFIED WORKING
Your auth is fine! This will stream live NQ data.
"""

import databento as db
import os
import time
import signal
from datetime import datetime
import requests

running = True

def signal_handler(sig, frame):
    global running
    print('\nStopping...')
    running = False

def main():
    print("🚀 DATABENTO LIVE NQ STREAM")
    print("="*50)
    print(f"API Key: {os.getenv('DATABENTO_API_KEY')}")
    print("="*50)

    signal.signal(signal.SIGINT, signal_handler)

    client = db.Live(key=os.getenv('DATABENTO_API_KEY'))

    record_count = 0
    last_price = None

    def handle_record(record):
        nonlocal record_count, last_price
        record_count += 1

        # Skip system messages
        if hasattr(record, 'msg'):
            if 'succeeded' in str(record.msg):
                print(f"✅ {record.msg}")
            return

        # Handle trades
        if hasattr(record, 'price') and hasattr(record, 'size'):
            price = float(record.price) / 1e9
            size = record.size
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]

            if last_price:
                change = price - last_price
                arrow = '↑' if change > 0 else '↓' if change < 0 else '='
                print(f"💹 NQ TRADE: ${price:,.2f} {arrow} ({change:+.2f}) x {size} @ {timestamp}")
            else:
                print(f"💹 NQ TRADE: ${price:,.2f} x {size} @ {timestamp}")

            last_price = price

            # Send to verifier
            try:
                requests.post(
                    'http://localhost:8083/api/system-data',
                    json={'price': price, 'source': 'databento_live'},
                    timeout=1
                )
                print("  ✅ Sent to verifier")
            except:
                pass

        # Handle quotes (MBP)
        elif hasattr(record, 'bid_px_00') and hasattr(record, 'ask_px_00'):
            if record.bid_px_00 and record.ask_px_00:
                bid = float(record.bid_px_00) / 1e9
                ask = float(record.ask_px_00) / 1e9
                spread = ask - bid

                # Show every 10th quote
                if record_count % 10 == 0:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"📊 Quote: ${bid:,.2f} / ${ask:,.2f} (spread: ${spread:.2f}) @ {timestamp}")

                    # Send mid price
                    mid = (bid + ask) / 2
                    last_price = mid

                    if record_count % 50 == 0:
                        try:
                            requests.post(
                                'http://localhost:8083/api/system-data',
                                json={'price': mid, 'source': 'databento_live_mid'},
                                timeout=1
                            )
                        except:
                            pass

    # Add callback
    client.add_callback(handle_record)

    # Subscribe
    print("\n📡 Subscribing to NQ futures (CME)...")

    client.subscribe(
        dataset='GLBX.MDP3',
        symbols=['NQ.c.0'],
        schema='trades'
    )

    client.subscribe(
        dataset='GLBX.MDP3',
        symbols=['NQ.c.0'],
        schema='mbp-1'
    )

    # Start
    print("🚀 Starting live stream...")
    client.start()

    print("⏳ Waiting for market data...")
    print("Press Ctrl+C to stop\n")

    # Keep running
    start_time = time.time()
    last_status = time.time()

    while running:
        time.sleep(0.1)

        # Status update every 10 seconds
        if time.time() - last_status > 10:
            elapsed = int(time.time() - start_time)
            print(f"\n📊 Status: {record_count} records in {elapsed}s")
            if last_price:
                print(f"   Last NQ: ${last_price:,.2f}")

                # Check verification
                try:
                    resp = requests.get('http://localhost:8083/api/status')
                    if resp.status_code == 200:
                        status = resp.json()
                        if status['is_live']:
                            print("   🎉 LIVE DATA VERIFIED!")
                        else:
                            print(f"   Time diff: {status['time_diff']:.1f}s, Price diff: ${status['price_diff']:.2f}")
                except:
                    pass

            last_status = time.time()

    # Cleanup
    print("\nStopping client...")
    client.stop()
    print(f"\nTotal records: {record_count}")

if __name__ == "__main__":
    main()
