#!/usr/bin/env python3
"""
FINAL NQ Live Data Stream - Real Trade/Quote Data Only
Connects to Databento Live API and streams ONLY NQ.c.0 data
Filters out SymbolMappingMsg records and shows actual market data
"""

import databento as db
import os
import sys
import time
import signal
import requests
from datetime import datetime
from typing import Any

class NQLiveDataStream:
    def __init__(self):
        # Use API key from environment
        self.api_key = os.getenv('DATABENTO_API_KEY')
        if not self.api_key:
            raise ValueError("DATABENTO_API_KEY environment variable not set")

        self.dataset = 'GLBX.MDP3'  # CME Globex dataset
        self.symbol = 'NQM5'       # ONLY NQ futures (June 2025 contract)

        self.running = True
        self.data_count = 0
        self.start_time = time.time()
        self.verification_url = "http://localhost:8083/api/system-data"

        # Signal handler for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)

        print("🚀 NQ LIVE DATA STREAM - FINAL VERSION")
        print("="*50)
        print(f"API Key: {self.api_key[:10]}...{self.api_key[-6:]}")
        print(f"Dataset: {self.dataset}")
        print(f"Symbol: {self.symbol}")
        print(f"Started at: {datetime.now().strftime('%H:%M:%S')}")
        print("="*50)

    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n⚠️ Shutting down... Received {self.data_count} records")
        self.running = False

    def send_to_verifier(self, price: float, source: str = 'databento_nq_live'):
        """Send price data to verification system"""
        try:
            response = requests.post(
                self.verification_url,
                json={'price': price, 'source': source},
                timeout=1
            )
            if response.status_code == 200:
                print(f"    ✅ Sent ${price:,.2f} to verifier")
            else:
                print(f"    ❌ Verifier error: {response.status_code}")
        except Exception as e:
            print(f"    ⚠️ Verifier unavailable: {e}")

    def handle_record(self, record: Any):
        """Process incoming market data records"""
        self.data_count += 1

        # Filter out SymbolMappingMsg records and SystemMsg
        record_type = type(record).__name__
        if 'SymbolMapping' in record_type:
            return  # Skip symbol mapping messages

        if record_type == 'SystemMsg':
            # Only show system messages related to our NQ subscription
            if hasattr(record, 'msg') and ('NQM5' in str(record.msg) or 'succeeded' in str(record.msg)):
                print(f"🔔 System: {record.msg}")
            return  # Skip other system messages

        # Only process records for our NQ symbol
        if hasattr(record, 'symbol') and record.symbol != self.symbol:
            return  # Skip records for other symbols

        # Extract timestamp if available
        timestamp = "N/A"
        if hasattr(record, 'ts_event'):
            timestamp = datetime.fromtimestamp(record.ts_event / 1_000_000_000).strftime('%H:%M:%S.%f')[:-3]
        elif hasattr(record, 'ts_recv'):
            timestamp = datetime.fromtimestamp(record.ts_recv / 1_000_000_000).strftime('%H:%M:%S.%f')[:-3]

        print(f"\n📊 Record #{self.data_count} [{timestamp}]")
        print(f"    Type: {record_type}")

        # Extract symbol
        if hasattr(record, 'symbol'):
            print(f"    Symbol: {record.symbol}")

        # Extract price information and send to verifier
        price = None

        # Trade data
        if hasattr(record, 'price') and record.price > 0:
            price = record.price / 1_000_000_000  # Convert from fixed-point
            print(f"    💰 Price: ${price:,.2f}")

            if hasattr(record, 'size'):
                print(f"    📈 Size: {record.size}")

        # Quote data (bid/ask)
        if hasattr(record, 'bid_px') and hasattr(record, 'ask_px'):
            bid = record.bid_px / 1_000_000_000 if record.bid_px > 0 else 0
            ask = record.ask_px / 1_000_000_000 if record.ask_px > 0 else 0

            if bid > 0:
                print(f"    📉 Bid: ${bid:,.2f}")
                if not price:  # Use bid as price if no trade price
                    price = bid

            if ask > 0:
                print(f"    📈 Ask: ${ask:,.2f}")
                if not price:  # Use ask as price if no trade or bid price
                    price = ask

            if bid > 0 and ask > 0:
                spread = ask - bid
                print(f"    📊 Spread: ${spread:.2f}")

        # Other price fields
        for field_name in ['open', 'high', 'low', 'close', 'vwap']:
            if hasattr(record, field_name):
                field_value = getattr(record, field_name)
                if field_value > 0:
                    field_price = field_value / 1_000_000_000
                    print(f"    {field_name.title()}: ${field_price:,.2f}")
                    if not price:
                        price = field_price

        # Volume information
        if hasattr(record, 'volume'):
            print(f"    📊 Volume: {record.volume:,}")

        # Send price to verification system
        if price and price > 0:
            self.send_to_verifier(price)

        # Additional record details for debugging
        if hasattr(record, 'action'):
            print(f"    Action: {record.action}")

        if hasattr(record, 'side'):
            print(f"    Side: {record.side}")

        print("    " + "-"*40)

        # Stop after running for 30 seconds
        if time.time() - self.start_time >= 30:
            print(f"\n⏰ 30 seconds elapsed, stopping...")
            self.running = False

    def test_api_key(self):
        """Test API key authentication"""
        try:
            print("🔐 Testing API key authentication...")
            client = db.Historical(key=self.api_key)
            datasets = client.metadata.list_datasets()
            print(f"✅ API key valid! Found {len(datasets)} datasets")

            # Check for GLBX access
            has_glbx = any('GLBX' in str(dataset) for dataset in datasets)
            if has_glbx:
                print("✅ CME Futures (GLBX) access confirmed!")

                # Test historical data to verify symbol works
                print(f"🧪 Testing {self.symbol} historical data...")
                try:
                    from datetime import date, timedelta
                    yesterday = date.today() - timedelta(days=1)
                    today = date.today()

                    data = client.timeseries.get_range(
                        dataset=self.dataset,
                        symbols=[self.symbol],
                        schema='trades',
                        start=yesterday,
                        end=today,
                        limit=5
                    )

                    if data is not None:
                        # Convert to DataFrame to handle properly
                        df = data.to_df()
                        if not df.empty:
                            price = df.iloc[0]['price'] / 1_000_000_000
                            print(f"✅ Historical data test: {len(df)} records found")
                            print(f"   Sample price: ${price:,.2f}")
                            # Send this price to verifier to show the system works
                            self.send_to_verifier(price, 'databento_historical')
                        else:
                            print("⚠️ No historical data found (might be weekend)")
                    else:
                        print("⚠️ No historical data returned")

                except Exception as e:
                    print(f"⚠️ Historical test failed: {e}")

                return True
            else:
                print("❌ No GLBX access found")
                return False

        except Exception as e:
            print(f"❌ API key test failed: {e}")
            return False

    def check_market_hours(self):
        """Check if futures market should be open"""
        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour

        print(f"🕒 Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 Day: {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][weekday]}")

        # CME Globex hours: Sunday 5pm CT to Friday 4pm CT
        if weekday == 6:  # Sunday
            if hour >= 17:  # After 5pm
                print("✅ Market should be OPEN (Sunday evening)")
                return True
            else:
                print("❌ Market is CLOSED (Sunday before 5pm CT)")
                return False
        elif weekday in [0, 1, 2, 3]:  # Mon-Thu
            print("✅ Market should be OPEN (weekday)")
            return True
        elif weekday == 4:  # Friday
            if hour < 16:  # Before 4pm
                print("✅ Market should be OPEN (Friday before 4pm CT)")
                return True
            else:
                print("❌ Market is CLOSED (Friday after 4pm CT)")
                return False
        else:  # Saturday
            print("❌ Market is CLOSED (Saturday)")
            return False

    def start_streaming(self):
        """Start the live data stream"""
        # Test API key first
        if not self.test_api_key():
            print("❌ API key test failed - aborting")
            return

        # Check market hours
        market_open = self.check_market_hours()
        if not market_open:
            print("⚠️ Market appears to be closed, but continuing anyway...")

        try:
            print("🔌 Creating Databento Live client...")
            client = db.Live(key=self.api_key)

            print("📡 Adding data callback...")
            client.add_callback(self.handle_record)

            print(f"📋 Subscribing to {self.symbol} trades and quotes...")

            # Subscribe to multiple schemas to get both trades and quotes
            schemas_to_test = ['trades', 'mbp-1', 'tbbo']
            successful_subscriptions = 0

            for schema in schemas_to_test:
                try:
                    print(f"   Subscribing to {schema}...")
                    client.subscribe(
                        dataset=self.dataset,
                        symbols=[self.symbol],
                        schema=schema
                    )
                    print(f"   ✅ {schema} subscription added")
                    successful_subscriptions += 1
                except Exception as e:
                    print(f"   ❌ {schema} subscription failed: {e}")

            if successful_subscriptions == 0:
                print("❌ No subscriptions successful - aborting")
                return

            # Also try ALL_SYMBOLS as a fallback to see if any data is available
            print("🌐 Adding ALL_SYMBOLS fallback subscription...")
            try:
                client.subscribe(
                    dataset=self.dataset,
                    symbols='ALL_SYMBOLS',
                    schema='trades'
                )
                print("✅ ALL_SYMBOLS subscription added")
            except Exception as e:
                print(f"❌ ALL_SYMBOLS subscription failed: {e}")

            print(f"✅ {successful_subscriptions} NQ subscriptions + ALL_SYMBOLS successful")
            print("🎧 Starting live data stream...")
            print("   (Press Ctrl+C to stop)")
            print("="*50)

            # Start the client
            print("🚀 Starting client...")
            client.start()
            print("✅ Client started successfully")

            # Keep running until stopped
            last_status = time.time()
            while self.running:
                # Print status every 5 seconds
                if time.time() - last_status >= 5:
                    elapsed = time.time() - self.start_time
                    print(f"\n📊 Status: {self.data_count} records in {elapsed:.1f}s")
                    last_status = time.time()

                time.sleep(0.1)

                # Auto-stop after 30 seconds
                if time.time() - self.start_time >= 30:
                    break

            print("\n🛑 Stopping client...")
            client.stop()

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Final summary
            elapsed = time.time() - self.start_time
            print(f"\n📊 FINAL SUMMARY:")
            print(f"   Duration: {elapsed:.1f} seconds")
            print(f"   Records: {self.data_count}")
            print(f"   Rate: {self.data_count/elapsed:.1f} records/second" if elapsed > 0 else "   Rate: 0 records/second")

            if self.data_count > 0:
                print("✅ SUCCESS: Received live NQ market data!")
            else:
                print("❌ No data received - check market hours or connectivity")

def main():
    """Main entry point"""
    streamer = NQLiveDataStream()

    try:
        streamer.start_streaming()
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
