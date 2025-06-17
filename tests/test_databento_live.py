#!/usr/bin/env python3
import databento as db
import os
from datetime import datetime

print('DATABENTO LIVE TEST')
print('='*40)

api_key = os.getenv('DATABENTO_API_KEY')
if not api_key:
    print("No API key found")
    exit(1)

live = db.Live(key=api_key)

try:
    # Subscribe to NQ
    print("Subscribing to NQ futures...")
    live.subscribe(
        dataset='GLBX.MDP3',
        symbols=['NQ.c.0'],
        schema='trades'
    )

    print("Iterating over live data...")
    count = 0

    for record in live:
        print(f"Record {count}: {type(record).__name__}")

        if hasattr(record, 'price'):
            price = float(record.price) / 1e9
            timestamp = datetime.now().isoformat()
            print(f"  NQ Trade: ${price:.2f} at {timestamp}")
        else:
            # Show what fields are available
            fields = [f for f in dir(record) if not f.startswith('_')]
            print(f"  Fields: {fields[:5]}...")  # First 5 fields

        count += 1
        if count >= 10:
            break

    print("\nStopping...")
    live.stop()
    print("Success!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
