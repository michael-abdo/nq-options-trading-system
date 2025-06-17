#!/usr/bin/env python3
import databento as db
import os

client = db.Live(key=os.getenv('DATABENTO_API_KEY'))

# Try subscribing to ALL CME symbols
print("Subscribing to ALL CME symbols...")

got_data = False

def handle_data(record):
    global got_data
    if not got_data:
        print(f"\nFIRST DATA RECEIVED!")
        print(f"Type: {type(record).__name__}")
        if hasattr(record, 'symbol'):
            print(f"Symbol: {record.symbol}")
        if hasattr(record, 'instrument_id'):
            print(f"Instrument ID: {record.instrument_id}")
        print(f"Record: {record}")
        got_data = True
        # Don't stop - let's see more

client.add_callback(handle_data)

# Subscribe to ALL instruments
client.subscribe(
    dataset='GLBX.MDP3',
    symbols=['ALL_SYMBOLS'],  # Special symbol for all
    schema='mbp-1'
)

print("Starting (waiting for ANY CME data)...")
client.start()

import time
time.sleep(10)

client.stop()

if not got_data:
    print("\nNo data received. Possible issues:")
    print("1. Market might be in a quiet period")
    print("2. Connection/firewall issues")
    print("3. Account permissions")

print("\nTrying system status check...")
