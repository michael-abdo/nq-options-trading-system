#!/usr/bin/env python3
"""
NQ Futures Live Price Streamer
Logs second-by-second NQ futures prices using Databento Live API
"""

import databento as db
from datetime import datetime
from utils.timezone_utils import get_eastern_time, get_utc_time
import signal
import sys
import os

# Configuration
import os
API_KEY = os.environ.get("DATABENTO_API_KEY", "your-api-key-here")
DATASET = "GLBX.MDP3"
SYMBOL = "NQM5"  # June 2025 E-mini NASDAQ-100

# Global variable to track last price for second-by-second updates
last_price = None
last_second = None

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n📊 Stream terminated by user")
    print("=" * 60)
    sys.exit(0)

def format_price(price):
    """Format price with commas"""
    return f"${price:,.2f}"

def on_trade(record):
    """Process each trade record"""
    global last_price, last_second

    # Extract trade data
    price = record.price / 1e9  # Convert from fixed-point to decimal
    size = record.size
    timestamp = datetime.fromtimestamp(record.ts_event / 1e9)  # Convert nanoseconds to seconds

    # Get current second
    current_second = timestamp.replace(microsecond=0)

    # Only print if it's a new second or first trade
    if last_second is None or current_second > last_second:
        # Calculate price change if we have a previous price
        if last_price is not None:
            change = price - last_price
            change_str = f"{change:+.2f}" if change != 0 else " 0.00"
            pct_change = (change / last_price) * 100
            pct_str = f"{pct_change:+.2f}%" if change != 0 else " 0.00%"
        else:
            change_str = "  N/A"
            pct_str = "   N/A"

        # Format output
        time_str = timestamp.strftime("%H:%M:%S")
        print(f"{time_str} | {format_price(price)} | {change_str} ({pct_str}) | Vol: {size}")

        # Update tracking variables
        last_second = current_second
        last_price = price

def main():
    """Main streaming function"""
    print("🔴 NQ FUTURES LIVE PRICE STREAM")
    print("=" * 60)
    print(f"Symbol: {SYMBOL} (E-mini NASDAQ-100 June 2025)")
    print(f"Dataset: {DATASET}")
    print(f"Started: {get_eastern_time().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print("TIME     | PRICE      | CHANGE    | VOLUME")
    print("-" * 60)

    # Set up signal handler for clean exit
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Create live client
        client = db.Live(key=API_KEY)

        # Subscribe to trades
        client.subscribe(
            dataset=DATASET,
            schema="trades",
            symbols=[SYMBOL],
            stype_in="raw_symbol"
        )

        # Start streaming
        for record in client:
            if hasattr(record, 'price'):  # Only process trade records
                on_trade(record)

    except Exception as e:
        print(f"\n❌ Streaming error: {e}")
        print("\nTroubleshooting:")
        print("1. Check if market is open (9:30 AM - 4:00 PM ET)")
        print("2. Verify API key has live data access")
        print("3. Ensure you have live subscription for GLBX.MDP3")

if __name__ == "__main__":
    main()
