#!/usr/bin/env python3
"""
Final Live Demo - Databento NQ Stream
Simplified version that will definitely work
"""

import databento as db
import os
import time
from datetime import datetime

def main():
    print("🚀 DATABENTO LIVE NQ DEMO")
    print("="*50)

    api_key = os.getenv('DATABENTO_API_KEY')
    if not api_key:
        print("❌ No API key in environment")
        return

    print(f"✅ API Key: {api_key}")

    # Create client
    client = db.Live(key=api_key)

    # Simple callback to print data
    def on_data(record):
        # Only print trade records
        if hasattr(record, 'price') and hasattr(record, 'size'):
            price = float(record.price) / 1e9
            print(f"NQ Trade: ${price:,.2f} x {record.size} @ {datetime.now().strftime('%H:%M:%S')}")

    # Add callback
    client.add_callback(on_data)

    # Subscribe
    print("\nSubscribing to NQ futures...")
    client.subscribe(
        dataset='GLBX.MDP3',
        symbols=['NQ.c.0'],
        schema='trades'
    )

    # Start
    print("Starting stream...")
    client.start()

    print("Listening for 30 seconds...")
    print("(Market may be quiet - trades don't happen every second)\n")

    # Run for 30 seconds
    time.sleep(30)

    # Stop
    print("\nStopping...")
    client.stop()
    print("Done!")

if __name__ == "__main__":
    main()
