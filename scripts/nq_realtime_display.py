#!/usr/bin/env python3
"""
NQ Real-Time Price Display
"""

import databento as db
from datetime import datetime
import pytz

import os
API_KEY = os.environ.get("DATABENTO_API_KEY", "your-api-key-here")

print("🔴 LIVE NQ FUTURES PRICES")
print("=" * 60)
print("Connecting...")

# Create client
client = db.Live(key=API_KEY)

# Subscribe
client.subscribe(
    dataset="GLBX.MDP3",
    schema="trades",
    symbols=["NQM5"]
)

print("✅ Connected to live feed!")
print("\nPRICE       | SIZE | TIME (ET)")
print("-" * 40)

count = 0
last_price = None

try:
    for msg in client:
        # Only process trades
        if hasattr(msg, 'price'):
            count += 1
            price = msg.price / 1e9
            size = msg.size

            # Get ET time
            et = pytz.timezone('US/Eastern')
            time_et = datetime.fromtimestamp(msg.ts_event / 1e9).astimezone(et)

            # Show price
            print(f"${price:>10,.2f} | {size:>4} | {time_et.strftime('%I:%M:%S %p')}")

            last_price = price

            # Stop after 20 trades for demo
            if count >= 20:
                print("\n[Demo limit reached - 20 trades]")
                break

except KeyboardInterrupt:
    print("\n[Stopped by user]")
except Exception as e:
    print(f"\nError: {e}")

if last_price:
    print(f"\nLatest price: ${last_price:,.2f}")
print(f"Total trades shown: {count}")
