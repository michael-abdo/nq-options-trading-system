#!/usr/bin/env python3
"""
Working Databento Live Stream
Based on official documentation approach
"""

import databento as db
import os
import signal
import sys
from datetime import datetime

# Global to control shutdown
running = True

def signal_handler(sig, frame):
    global running
    print('\nStopping...')
    running = False

def main():
    print("DATABENTO LIVE NQ STREAM")
    print("="*50)

    api_key = os.getenv('DATABENTO_API_KEY')
    if not api_key:
        print("Error: DATABENTO_API_KEY not set")
        return

    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Create live client
    client = db.Live(key=api_key)

    # Counter for records
    record_count = 0

    # Callback function
    def handle_record(record):
        global record_count
        record_count += 1

        # Print record info
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"\n[{timestamp}] Record #{record_count}")
        print(f"  Type: {type(record).__name__}")

        # Handle different record types
        if hasattr(record, 'symbol'):
            print(f"  Symbol: {record.symbol}")

        if hasattr(record, 'price'):
            # Trade record
            price = float(record.price) / 1e9
            size = getattr(record, 'size', 0)
            print(f"  Trade: ${price:.2f} x {size}")

            # Send to verifier
            try:
                import requests
                requests.post(
                    'http://localhost:8083/api/system-data',
                    json={'price': price, 'source': 'databento_live'},
                    timeout=1
                )
                print("  ✅ Sent to verifier")
            except:
                pass

        elif hasattr(record, 'bid_px_00') and hasattr(record, 'ask_px_00'):
            # MBP record
            bid = float(record.bid_px_00) / 1e9 if record.bid_px_00 else 0
            ask = float(record.ask_px_00) / 1e9 if record.ask_px_00 else 0

            if bid > 0 and ask > 0:
                mid = (bid + ask) / 2
                spread = ask - bid
                print(f"  Quote: Bid ${bid:.2f} / Ask ${ask:.2f}")
                print(f"  Mid: ${mid:.2f}, Spread: ${spread:.2f}")

                # Send mid price to verifier
                try:
                    import requests
                    requests.post(
                        'http://localhost:8083/api/system-data',
                        json={'price': mid, 'source': 'databento_live_mid'},
                        timeout=1
                    )
                except:
                    pass

    # Add callback
    client.add_callback(handle_record)

    # Subscribe to data
    print("\nSubscribing to NQ futures...")
    print("  Dataset: GLBX.MDP3 (CME)")
    print("  Symbol: NQ.c.0")
    print("  Schema: mbp-1 (top of book)")

    client.subscribe(
        dataset='GLBX.MDP3',
        symbols=['NQ.c.0'],
        schema='mbp-1'  # Top of book - usually more active than trades
    )

    # Also try trades
    client.subscribe(
        dataset='GLBX.MDP3',
        symbols=['NQ.c.0'],
        schema='trades'
    )

    print("\nStarting live stream...")
    print("Press Ctrl+C to stop\n")

    try:
        # Start the client
        client.start()

        # Keep running until interrupted
        while running:
            # The callback handles all data
            import time
            time.sleep(0.1)

            # Show status every 10 seconds
            if record_count > 0 and record_count % 100 == 0:
                print(f"\n📊 Processed {record_count} records...")

    except Exception as e:
        print(f"\nError: {e}")
    finally:
        print("\nStopping client...")
        try:
            client.stop()
        except:
            pass
        print(f"Total records: {record_count}")

if __name__ == "__main__":
    main()
