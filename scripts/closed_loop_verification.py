#!/usr/bin/env python3
"""
Closed Loop Verification System
Continuously streams Databento live NQ data and verifies against Tradovate
"""

import databento as db
import os
import sys
import time
import requests
import asyncio
from datetime import datetime
import threading

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ClosedLoopVerifier:
    def __init__(self):
        self.api_key = os.getenv('DATABENTO_API_KEY')
        self.verification_url = "http://localhost:8083"
        self.latest_databento_price = None
        self.latest_databento_time = None
        self.is_verified_live = False
        self.running = True

    def send_system_data(self, price):
        """Send Databento price to verification system"""
        try:
            response = requests.post(
                f"{self.verification_url}/api/system-data",
                json={'price': price, 'source': 'databento_live_cme'},
                timeout=2
            )
            if response.status_code == 200:
                self.latest_databento_price = price
                self.latest_databento_time = datetime.now()
                return True
        except:
            pass
        return False

    def check_verification_status(self):
        """Check if data is verified as live"""
        try:
            response = requests.get(f"{self.verification_url}/api/status", timeout=2)
            if response.status_code == 200:
                status = response.json()
                self.is_verified_live = status.get('is_live', False)
                return status
        except:
            pass
        return None

    def stream_databento_nq(self):
        """Stream live NQ data from Databento CME"""
        print("🚀 Starting Databento NQ live stream...")

        live = db.Live(key=self.api_key)

        try:
            # Subscribe to NQ futures on CME
            live.subscribe(
                dataset='GLBX.MDP3',
                symbols=['NQ.c.0'],
                schema='trades'
            )

            # Don't call start() - just iterate directly
            print("✅ Connected to Databento CME live feed!")

            for record in live:
                if not self.running:
                    break

                try:

                    if hasattr(record, 'price'):
                        price = float(record.price) / 1e9
                        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]

                        print(f"📊 Databento NQ: ${price:,.2f} at {timestamp}")

                        # Send to verification system
                        if self.send_system_data(price):
                            print(f"   ✅ Sent to verifier")

                        # Check verification status
                        status = self.check_verification_status()
                        if status:
                            if self.is_verified_live:
                                print(f"   🎉 VERIFIED LIVE! Time diff: {status['time_diff']:.1f}s, Price diff: ${status['price_diff']:.2f}")
                            else:
                                print(f"   ⏳ Not verified: {status['message']}")

                        # Small delay to not overwhelm
                        time.sleep(0.5)

                except Exception as e:
                    print(f"Record processing error: {e}")
                    continue

        except Exception as e:
            print(f"❌ Databento connection error: {e}")
        finally:
            try:
                live.stop()
            except:
                pass

    def monitor_tradovate(self):
        """Monitor for Tradovate reference data updates"""
        print("👀 Monitoring for Tradovate reference data...")

        last_check = None
        while self.running:
            try:
                status = self.check_verification_status()
                if status:
                    tradovate_time = status.get('last_check')
                    if tradovate_time != last_check:
                        last_check = tradovate_time
                        print(f"\n📋 Tradovate Reference: ${status['tradovate_price']:,.2f}")
                        print(f"   Time: {tradovate_time}")

                        if self.is_verified_live:
                            print("   ✅ DATA VERIFIED AS LIVE!")
                        else:
                            print(f"   ⚠️ Waiting for fresh Tradovate data (currently {status['time_diff']:.0f}s old)")
                            print("   💡 Click 'Copy Trading Data' in Tradovate to update reference")

                time.sleep(2)
            except:
                time.sleep(2)

    def run_closed_loop(self):
        """Run the closed feedback loop"""
        print("🔄 CLOSED LOOP VERIFICATION SYSTEM")
        print("="*60)
        print("Goal: Verify Databento live data matches Tradovate reference")
        print("Criteria: <5 second time difference AND <$10 price difference")
        print("="*60)
        print()

        # Start verification server if not running
        try:
            response = requests.get(f"{self.verification_url}/api/status", timeout=1)
        except:
            print("⚠️ Verification server not running. Please run:")
            print("   python3 tests/chrome/live_data_verification.py")
            return

        # Start threads
        databento_thread = threading.Thread(target=self.stream_databento_nq)
        monitor_thread = threading.Thread(target=self.monitor_tradovate)

        databento_thread.start()
        monitor_thread.start()

        print("\n🎯 Closed loop running! Press Ctrl+C to stop.\n")

        try:
            while self.running:
                time.sleep(1)

                # Check if we achieved verification
                if self.is_verified_live:
                    print("\n" + "="*60)
                    print("🎉 SUCCESS! LIVE DATA VERIFIED!")
                    print("✅ Databento CME feed is confirmed LIVE")
                    print("✅ Matching Tradovate reference within tolerances")
                    print("="*60)

                    # Continue running to maintain verification

        except KeyboardInterrupt:
            print("\n\n👋 Stopping closed loop...")
            self.running = False

        # Wait for threads
        databento_thread.join(timeout=5)
        monitor_thread.join(timeout=5)

        print("✅ Closed loop stopped")

def main():
    """Main entry point"""
    verifier = ClosedLoopVerifier()

    if not verifier.api_key:
        print("❌ DATABENTO_API_KEY not found")
        return

    # Check if market is open
    now = datetime.now()
    if now.weekday() == 5:  # Saturday
        print("⚠️ Market is closed on Saturday")
        print("  Futures market opens Sunday 6PM ET")
    elif now.weekday() == 6 and now.hour < 18:  # Sunday before 6PM
        print("⚠️ Market opens at 6PM ET on Sunday")

    # Run the closed loop
    verifier.run_closed_loop()

if __name__ == "__main__":
    main()
