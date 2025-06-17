#!/usr/bin/env python3
"""
Final Closed Loop Verification
Databento Live NQ vs Tradovate Reference
"""

import databento as db
import os
import sys
import time
import requests
from datetime import datetime
import signal

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class FinalClosedLoop:
    def __init__(self):
        self.running = True
        self.api_key = os.getenv('DATABENTO_API_KEY')
        self.client = None
        self.record_count = 0
        self.trade_count = 0
        self.quote_count = 0
        self.last_price = None

    def handle_record(self, record):
        """Process each record from Databento"""
        self.record_count += 1

        # Skip system messages
        if hasattr(record, 'msg'):
            if self.record_count == 1:
                print(f"✅ Connected: {record.msg}")
            return

        # Handle trade records
        if hasattr(record, 'price') and hasattr(record, 'size'):
            self.trade_count += 1
            price = float(record.price) / 1e9
            size = record.size

            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]

            # Show price movement
            if self.last_price:
                change = price - self.last_price
                arrow = '↑' if change > 0 else '↓' if change < 0 else '='
                print(f"\n💹 NQ TRADE: ${price:,.2f} {arrow} ({change:+.2f}) x {size} @ {timestamp}")
            else:
                print(f"\n💹 NQ TRADE: ${price:,.2f} x {size} @ {timestamp}")

            self.last_price = price

            # Send to verifier
            self.send_to_verifier(price, 'trade')

        # Handle quote records (MBP)
        elif hasattr(record, 'bid_px_00') and hasattr(record, 'ask_px_00'):
            bid_px = record.bid_px_00
            ask_px = record.ask_px_00

            if bid_px and ask_px:
                self.quote_count += 1
                bid = float(bid_px) / 1e9
                ask = float(ask_px) / 1e9
                mid = (bid + ask) / 2
                spread = ask - bid

                # Only show every 10th quote to reduce noise
                if self.quote_count % 10 == 0:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"  📊 Quote: ${bid:,.2f} / ${ask:,.2f} (spread: ${spread:.2f}) @ {timestamp}")

                    # Update last price with mid
                    self.last_price = mid

                    # Send mid price to verifier
                    if self.quote_count % 50 == 0:  # Every 50 quotes
                        self.send_to_verifier(mid, 'mid')

    def send_to_verifier(self, price, source_type):
        """Send price to verification system"""
        try:
            response = requests.post(
                'http://localhost:8083/api/system-data',
                json={'price': price, 'source': f'databento_live_{source_type}'},
                timeout=1
            )
            if response.status_code == 200:
                print(f"  ✅ Sent to verifier: ${price:,.2f}")

                # Check verification status
                self.check_verification()
        except:
            pass

    def check_verification(self):
        """Check if we achieved live verification"""
        try:
            response = requests.get('http://localhost:8083/api/status', timeout=1)
            if response.status_code == 200:
                status = response.json()

                if status['is_live']:
                    print("\n" + "="*60)
                    print("🎉 LIVE DATA VERIFIED!")
                    print(f"✅ Time difference: {status['time_diff']:.1f} seconds")
                    print(f"✅ Price difference: ${status['price_diff']:.2f}")
                    print(f"✅ Databento: ${status['system_price']:,.2f}")
                    print(f"✅ Tradovate: ${status['tradovate_price']:,.2f}")
                    print("="*60)
                else:
                    time_diff = status['time_diff']
                    if time_diff > 60:
                        print(f"  ⏳ Waiting for fresh Tradovate data ({time_diff:.0f}s old)")
        except:
            pass

    def run(self):
        """Main execution loop"""
        print("🔄 FINAL CLOSED LOOP VERIFICATION")
        print("="*60)
        print("Databento Live NQ (CME) vs Tradovate Reference")
        print("="*60)

        # Check verification server
        try:
            requests.get('http://localhost:8083/api/status', timeout=1)
        except:
            print("⚠️  Please start verification server:")
            print("   python3 tests/chrome/live_data_verification.py")
            return

        # Signal handler
        def stop_handler(sig, frame):
            print("\n\nStopping...")
            self.running = False
        signal.signal(signal.SIGINT, stop_handler)

        # Create client
        self.client = db.Live(key=self.api_key)
        self.client.add_callback(self.handle_record)

        # Subscribe to both trades and quotes
        print("\n📡 Subscribing to NQ futures...")

        self.client.subscribe(
            dataset='GLBX.MDP3',
            symbols=['NQ.c.0'],
            schema='trades'
        )

        self.client.subscribe(
            dataset='GLBX.MDP3',
            symbols=['NQ.c.0'],
            schema='mbp-1'  # Top of book quotes
        )

        print("🚀 Starting live stream...")
        print("⏳ Waiting for market data...")
        print("\n💡 To complete verification:")
        print("   1. Click 'Copy Trading Data' in Tradovate")
        print("   2. Fresh reference data will trigger verification")
        print("\nPress Ctrl+C to stop\n")

        # Start client
        self.client.start()

        # Status updates
        last_status_time = time.time()

        # Main loop
        while self.running:
            time.sleep(0.1)

            # Show status every 30 seconds
            if time.time() - last_status_time > 30:
                print(f"\n📊 Status: {self.record_count} records, {self.trade_count} trades, {self.quote_count} quotes")
                if self.last_price:
                    print(f"   Last NQ price: ${self.last_price:,.2f}")
                last_status_time = time.time()

        # Cleanup
        print("\nStopping client...")
        self.client.stop()

        print(f"\n📊 Final Statistics:")
        print(f"   Total records: {self.record_count}")
        print(f"   Trades: {self.trade_count}")
        print(f"   Quotes: {self.quote_count}")
        if self.last_price:
            print(f"   Last price: ${self.last_price:,.2f}")

def main():
    loop = FinalClosedLoop()
    loop.run()

if __name__ == "__main__":
    main()
