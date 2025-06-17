#!/usr/bin/env python3
"""
Comprehensive Databento Live Data Diagnostic Script
Tests connection, symbols, schemas, and data flow
"""

import databento as db
import os
import sys
import time
import signal
from datetime import datetime
import asyncio
import websockets
import json
import requests
from typing import Dict, List, Any

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_success(text: str):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_warning(text: str):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_error(text: str):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text: str):
    print(f"{Colors.OKBLUE}ℹ️  {text}{Colors.ENDC}")

class DatabentoCompleteDiagnostic:
    def __init__(self):
        self.api_key = os.getenv('DATABENTO_API_KEY')
        if not self.api_key:
            raise ValueError("DATABENTO_API_KEY environment variable not set")

        self.dataset = 'GLBX.MDP3'
        self.test_results = {}
        self.data_received = {}
        self.running = True

        # Test configurations
        self.test_symbols = [
            'NQ.c.0',      # E-mini Nasdaq continuous
            'ES.c.0',      # E-mini S&P continuous
            'ESM5.c.0',    # E-mini S&P June 2025
            'NQM5.c.0',    # E-mini Nasdaq June 2025
            'YM.c.0',      # E-mini Dow continuous
            'RTY.c.0',     # E-mini Russell continuous
            'CL.c.0',      # Crude Oil continuous
            'GC.c.0',      # Gold continuous
            'ALL_SYMBOLS'  # Special case for all symbols
        ]

        self.test_schemas = [
            'trades',      # Trade data
            'mbp-1',       # Market by price (top of book)
            'mbp-10',      # Market by price (10 levels)
            'mbo',         # Market by order
            'tbbo',        # Top bid/offer
            'bbo-1s',      # Best bid/offer 1 second
            'ohlcv-1s',    # OHLCV 1 second bars
            'ohlcv-1m',    # OHLCV 1 minute bars
            'definition',  # Symbol definitions
            'imbalance',   # Order imbalance
            'statistics'   # Exchange statistics
        ]

        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, sig, frame):
        print_warning("\nReceived interrupt signal, stopping...")
        self.running = False

    def test_environment(self):
        """Test environment setup"""
        print_header("1. ENVIRONMENT DIAGNOSTIC")

        # Check API key
        print_info(f"API Key: {self.api_key[:10]}...{self.api_key[-6:]}")

        # Check databento package
        try:
            import databento
            version = databento.__version__ if hasattr(databento, '__version__') else 'unknown'
            print_success(f"Databento package installed (version: {version})")
        except ImportError:
            print_error("Databento package not installed!")
            return False

        # Test network connectivity
        try:
            response = requests.get('https://api.databento.com/v0', timeout=5)
            print_success(f"Network connectivity OK (status: {response.status_code})")
        except Exception as e:
            print_error(f"Network connectivity failed: {e}")
            return False

        # Test API authentication
        try:
            client = db.Historical(key=self.api_key)
            # Try a simple metadata request
            metadata = client.metadata.list_datasets()
            print_success(f"API authentication successful! Found {len(metadata)} datasets")

            # Check for futures access
            has_futures = any('GLBX.MDP3' in str(d) for d in metadata)
            if has_futures:
                print_success("CME Futures (GLBX.MDP3) access confirmed!")
            else:
                print_warning("CME Futures access not found in datasets")

        except Exception as e:
            print_error(f"API authentication failed: {e}")
            return False

        return True

    def test_live_client_creation(self):
        """Test creating live client"""
        print_header("2. LIVE CLIENT CREATION")

        try:
            client = db.Live(key=self.api_key)
            print_success("Live client created successfully")

            # Test client properties
            if hasattr(client, 'dataset'):
                print_info(f"Default dataset: {client.dataset}")

            client.stop()
            return True

        except Exception as e:
            print_error(f"Failed to create live client: {e}")
            return False

    def test_symbol_schemas(self):
        """Test all symbol and schema combinations"""
        print_header("3. SYMBOL & SCHEMA TESTING")

        results = {}

        for symbol in self.test_symbols[:3]:  # Test first 3 symbols
            print(f"\n{Colors.BOLD}Testing symbol: {symbol}{Colors.ENDC}")
            results[symbol] = {}

            for schema in self.test_schemas[:5]:  # Test first 5 schemas
                result = self._test_single_subscription(symbol, schema)
                results[symbol][schema] = result

                if result['success']:
                    print_success(f"  {schema}: {result['message']}")
                else:
                    print_error(f"  {schema}: {result['message']}")

                time.sleep(0.5)  # Brief pause between tests

        self.test_results['symbol_schemas'] = results
        return any(any(r['success'] for r in symbol_results.values())
                  for symbol_results in results.values())

    def _test_single_subscription(self, symbol: str, schema: str) -> Dict[str, Any]:
        """Test a single symbol/schema combination"""
        client = None
        data_count = 0
        messages = []
        start_time = time.time()

        def handle_record(record):
            nonlocal data_count, messages
            data_count += 1

            # Capture system messages
            if hasattr(record, 'msg'):
                messages.append(str(record.msg))

            # Store data info
            record_type = type(record).__name__
            if record_type not in self.data_received:
                self.data_received[record_type] = 0
            self.data_received[record_type] += 1

            # Stop after receiving some data
            if data_count >= 10:
                client.stop()

        try:
            client = db.Live(key=self.api_key)
            client.add_callback(handle_record)

            # Subscribe
            if symbol == 'ALL_SYMBOLS':
                client.subscribe(
                    dataset=self.dataset,
                    symbols='ALL_SYMBOLS',
                    schema=schema
                )
            else:
                client.subscribe(
                    dataset=self.dataset,
                    symbols=[symbol],
                    schema=schema
                )

            # Start client
            client.start()

            # Wait for data (max 5 seconds)
            wait_start = time.time()
            while data_count == 0 and (time.time() - wait_start) < 5 and self.running:
                time.sleep(0.1)

            client.stop()

            if data_count > 0:
                return {
                    'success': True,
                    'message': f"Received {data_count} records in {time.time()-start_time:.1f}s",
                    'data_count': data_count,
                    'messages': messages
                }
            else:
                return {
                    'success': False,
                    'message': f"No data received after 5s wait",
                    'data_count': 0,
                    'messages': messages
                }

        except Exception as e:
            if client:
                try:
                    client.stop()
                except:
                    pass
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'data_count': 0,
                'messages': messages
            }

    def test_all_symbols_stream(self):
        """Test ALL_SYMBOLS to see if any data flows"""
        print_header("4. ALL_SYMBOLS STREAM TEST")

        print_info("Testing ALL_SYMBOLS to detect any available data...")

        client = None
        data_count = 0
        unique_symbols = set()
        start_time = time.time()

        def handle_record(record):
            nonlocal data_count
            data_count += 1

            # Track unique symbols
            if hasattr(record, 'symbol'):
                unique_symbols.add(record.symbol)

            # Print first few records
            if data_count <= 5:
                print_info(f"Record {data_count}: {type(record).__name__}")
                if hasattr(record, 'symbol'):
                    print(f"  Symbol: {record.symbol}")
                if hasattr(record, 'price'):
                    print(f"  Price: {record.price}")
                if hasattr(record, 'msg'):
                    print(f"  Message: {record.msg}")

        try:
            client = db.Live(key=self.api_key)
            client.add_callback(handle_record)

            print_info("Subscribing to ALL_SYMBOLS with trades schema...")
            client.subscribe(
                dataset=self.dataset,
                symbols='ALL_SYMBOLS',
                schema='trades'
            )

            client.start()

            # Wait for data
            print_info("Waiting for any market data (30 seconds)...")
            wait_start = time.time()
            last_update = time.time()

            while (time.time() - wait_start) < 30 and self.running:
                if time.time() - last_update > 5:
                    print_info(f"Status: {data_count} records from {len(unique_symbols)} symbols")
                    last_update = time.time()
                time.sleep(0.1)

            client.stop()

            if data_count > 0:
                print_success(f"Received {data_count} records from {len(unique_symbols)} unique symbols!")
                print_info("Sample symbols seen: " + ", ".join(list(unique_symbols)[:10]))
                return True
            else:
                print_warning("No data received from ALL_SYMBOLS stream")
                return False

        except Exception as e:
            print_error(f"ALL_SYMBOLS test failed: {e}")
            if client:
                try:
                    client.stop()
                except:
                    pass
            return False

    def test_websocket_direct(self):
        """Test direct WebSocket connection"""
        print_header("5. DIRECT WEBSOCKET TEST")

        async def ws_test():
            ws_urls = [
                "wss://api.databento.com/v0/stream",
                "wss://api.databento.com:13000",
                "wss://stream.databento.com/v0"
            ]

            for url in ws_urls:
                print_info(f"Testing WebSocket URL: {url}")

                try:
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "X-API-Key": self.api_key,
                        "User-Agent": "databento-diagnostic/1.0"
                    }

                    async with websockets.connect(
                        url,
                        extra_headers=headers,
                        ping_interval=20,
                        timeout=10
                    ) as ws:
                        print_success(f"Connected to {url}")

                        # Try to authenticate
                        auth_msg = {
                            "type": "auth",
                            "api_key": self.api_key
                        }
                        await ws.send(json.dumps(auth_msg))

                        # Wait for response
                        try:
                            response = await asyncio.wait_for(ws.recv(), timeout=5)
                            print_info(f"Response: {response}")
                        except asyncio.TimeoutError:
                            print_warning("No response received")

                        await ws.close()

                except Exception as e:
                    print_error(f"Failed to connect to {url}: {e}")

        try:
            asyncio.run(ws_test())
            return True
        except Exception as e:
            print_error(f"WebSocket test failed: {e}")
            return False

    def test_market_hours(self):
        """Check if market is open"""
        print_header("6. MARKET HOURS CHECK")

        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour

        print_info(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print_info(f"Day of week: {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][weekday]}")

        # CME Globex hours (Sunday 5pm CT to Friday 4pm CT)
        if weekday == 6:  # Sunday
            if hour >= 17:  # After 5pm
                print_success("Market should be OPEN (Sunday evening)")
                return True
            else:
                print_warning("Market is CLOSED (Sunday before 5pm CT)")
                return False
        elif weekday in [0, 1, 2, 3]:  # Mon-Thu
            print_success("Market should be OPEN (weekday)")
            return True
        elif weekday == 4:  # Friday
            if hour < 16:  # Before 4pm
                print_success("Market should be OPEN (Friday before 4pm CT)")
                return True
            else:
                print_warning("Market is CLOSED (Friday after 4pm CT)")
                return False
        else:  # Saturday
            print_warning("Market is CLOSED (Saturday)")
            return False

    def generate_report(self):
        """Generate diagnostic report"""
        print_header("DIAGNOSTIC REPORT")

        print(f"\n{Colors.BOLD}Test Summary:{Colors.ENDC}")

        # Data received summary
        if self.data_received:
            print_success(f"Total data types received: {len(self.data_received)}")
            for record_type, count in self.data_received.items():
                print(f"  - {record_type}: {count} records")
        else:
            print_error("No data received during tests")

        # Symbol/Schema results
        if 'symbol_schemas' in self.test_results:
            print(f"\n{Colors.BOLD}Symbol/Schema Results:{Colors.ENDC}")
            for symbol, schemas in self.test_results['symbol_schemas'].items():
                working_schemas = [s for s, r in schemas.items() if r['success']]
                if working_schemas:
                    print_success(f"{symbol}: {', '.join(working_schemas)}")
                else:
                    print_error(f"{symbol}: No working schemas")

        # Recommendations
        print(f"\n{Colors.BOLD}Recommendations:{Colors.ENDC}")
        if self.data_received:
            print_info("✓ Your connection is working! Data is flowing.")
            print_info("✓ Use the working symbol/schema combinations from above")
        else:
            print_warning("⚠ No data received. Possible causes:")
            print_warning("  - Market might be closed")
            print_warning("  - Subscription permissions")
            print_warning("  - Network/firewall issues")
            print_warning("  - Try ALL_SYMBOLS to see any available data")

    def run_full_diagnostic(self):
        """Run complete diagnostic suite"""
        print_header("DATABENTO LIVE DATA DIAGNOSTIC")
        print_info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Run tests
        tests = [
            ("Environment", self.test_environment),
            ("Live Client", self.test_live_client_creation),
            ("Market Hours", self.test_market_hours),
            ("Symbol/Schema", self.test_symbol_schemas),
            ("ALL_SYMBOLS", self.test_all_symbols_stream),
            ("WebSocket Direct", self.test_websocket_direct)
        ]

        results = {}
        for test_name, test_func in tests:
            if not self.running:
                print_warning("Diagnostic interrupted")
                break

            try:
                result = test_func()
                results[test_name] = result

                if result:
                    print_success(f"{test_name} test: PASSED")
                else:
                    print_error(f"{test_name} test: FAILED")

            except Exception as e:
                print_error(f"{test_name} test error: {e}")
                results[test_name] = False

            time.sleep(1)  # Brief pause between major tests

        # Generate report
        self.generate_report()

        # Overall result
        print_header("OVERALL RESULT")
        if any(results.values()) and self.data_received:
            print_success("✅ DATABENTO CONNECTION IS WORKING!")
            print_info("Some data was successfully received")
        else:
            print_error("❌ DATABENTO CONNECTION ISSUES DETECTED")
            print_info("Review the diagnostic output above for details")

def main():
    """Main entry point"""
    diagnostic = DatabentoCompleteDiagnostic()

    try:
        diagnostic.run_full_diagnostic()
    except KeyboardInterrupt:
        print_warning("\nDiagnostic interrupted by user")
    except Exception as e:
        print_error(f"Diagnostic failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
