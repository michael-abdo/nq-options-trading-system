#!/usr/bin/env python3
"""
Live Data Hunter - Aggressive Search for REAL Live Data
Tests multiple sources to find truly live NQ data
"""

import asyncio
import os
import sys
import time
import requests
import json
from datetime import datetime, timezone
import concurrent.futures

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class LiveDataHunter:
    def __init__(self):
        self.verification_url = "http://localhost:8083/api/system-data"
        self.results = {}

    def send_to_verifier(self, price, source):
        """Send price data to verification system"""
        try:
            response = requests.post(
                self.verification_url,
                json={'price': price, 'source': source},
                timeout=2
            )
            if response.status_code == 200:
                print(f"✅ {source}: ${price:,.2f} sent to verifier")
                return True
            else:
                print(f"❌ {source}: Failed to send to verifier")
                return False
        except Exception as e:
            print(f"❌ {source}: Verifier error - {e}")
            return False

    def test_yahoo_finance(self):
        """Test Yahoo Finance real-time quotes"""
        try:
            # NQ futures on Yahoo
            symbols = ['NQ=F', 'NQM24.CME', 'NQU24.CME']

            for symbol in symbols:
                try:
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                    params = {
                        'interval': '1m',
                        'range': '1d',
                        'includePrePost': 'true'
                    }

                    response = requests.get(url, params=params, timeout=5)

                    if response.status_code == 200:
                        data = response.json()

                        if 'chart' in data and data['chart']['result']:
                            result = data['chart']['result'][0]
                            meta = result.get('meta', {})
                            current_price = meta.get('regularMarketPrice')

                            if current_price:
                                print(f"📊 Yahoo {symbol}: ${current_price:,.2f}")
                                self.send_to_verifier(current_price, f'yahoo_{symbol}')
                                self.results[f'yahoo_{symbol}'] = current_price
                                return current_price

                except Exception as e:
                    print(f"❌ Yahoo {symbol} failed: {e}")

            return None

        except Exception as e:
            print(f"❌ Yahoo Finance test failed: {e}")
            return None

    def test_alpha_vantage(self):
        """Test Alpha Vantage real-time data"""
        api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            print("⚠️ ALPHA_VANTAGE_API_KEY not set")
            return None

        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': 'NQ',
                'apikey': api_key
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if 'Global Quote' in data:
                    quote = data['Global Quote']
                    price = float(quote.get('05. price', 0))

                    if price > 0:
                        print(f"📊 Alpha Vantage: ${price:,.2f}")
                        self.send_to_verifier(price, 'alpha_vantage')
                        self.results['alpha_vantage'] = price
                        return price

            print(f"❌ Alpha Vantage response: {response.text[:200]}")
            return None

        except Exception as e:
            print(f"❌ Alpha Vantage test failed: {e}")
            return None

    def test_quandl(self):
        """Test Quandl/NASDAQ Data Link"""
        api_key = os.getenv('QUANDL_API_KEY')
        if not api_key:
            print("⚠️ QUANDL_API_KEY not set")
            return None

        try:
            # Try NQ futures from CME
            url = "https://data.nasdaq.com/api/v3/datasets/CHRIS/CME_NQ1.json"
            params = {
                'api_key': api_key,
                'rows': 1
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if 'dataset' in data and data['dataset']['data']:
                    latest = data['dataset']['data'][0]
                    price = latest[4]  # Close price

                    print(f"📊 Quandl: ${price:,.2f}")
                    self.send_to_verifier(price, 'quandl')
                    self.results['quandl'] = price
                    return price

            return None

        except Exception as e:
            print(f"❌ Quandl test failed: {e}")
            return None

    def test_finnhub(self):
        """Test Finnhub real-time data"""
        api_key = os.getenv('FINNHUB_API_KEY')
        if not api_key:
            print("⚠️ FINNHUB_API_KEY not set")
            return None

        try:
            url = "https://finnhub.io/api/v1/quote"
            params = {
                'symbol': 'NQ',
                'token': api_key
            }

            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                price = data.get('c', 0)  # Current price

                if price > 0:
                    print(f"📊 Finnhub: ${price:,.2f}")
                    self.send_to_verifier(price, 'finnhub')
                    self.results['finnhub'] = price
                    return price

            return None

        except Exception as e:
            print(f"❌ Finnhub test failed: {e}")
            return None

    def test_iex_cloud(self):
        """Test IEX Cloud data"""
        api_key = os.getenv('IEX_CLOUD_API_KEY')
        if not api_key:
            print("⚠️ IEX_CLOUD_API_KEY not set")
            return None

        try:
            url = f"https://cloud.iexapis.com/stable/stock/NQ/quote"
            params = {'token': api_key}

            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                price = data.get('latestPrice', 0)

                if price > 0:
                    print(f"📊 IEX Cloud: ${price:,.2f}")
                    self.send_to_verifier(price, 'iex_cloud')
                    self.results['iex_cloud'] = price
                    return price

            return None

        except Exception as e:
            print(f"❌ IEX Cloud test failed: {e}")
            return None

    def test_webscraping_cme(self):
        """Scrape CME Group directly for NQ price"""
        try:
            url = "https://www.cmegroup.com/trading/equity-index/us-index/e-mini-nasdaq-100.html"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                # Look for price patterns in the HTML
                import re

                # Pattern to find price-like numbers
                price_patterns = [
                    r'"last":\s*"?([\d,]+\.?\d*)"?',
                    r'"price":\s*"?([\d,]+\.?\d*)"?',
                    r'data-price="([\d,]+\.?\d*)"',
                    r'>(\d{4,5}\.\d{2})<'
                ]

                for pattern in price_patterns:
                    matches = re.findall(pattern, response.text)
                    for match in matches:
                        try:
                            price = float(match.replace(',', ''))
                            if 20000 < price < 25000:  # Reasonable NQ range
                                print(f"📊 CME Scraping: ${price:,.2f}")
                                self.send_to_verifier(price, 'cme_scraping')
                                self.results['cme_scraping'] = price
                                return price
                        except:
                            continue

            return None

        except Exception as e:
            print(f"❌ CME scraping failed: {e}")
            return None

    def run_all_tests(self):
        """Run all data source tests concurrently"""
        print("🚀 LIVE DATA HUNTER - Testing All Sources")
        print("="*60)

        # List of test functions
        tests = [
            self.test_yahoo_finance,
            self.test_alpha_vantage,
            self.test_quandl,
            self.test_finnhub,
            self.test_iex_cloud,
            self.test_webscraping_cme
        ]

        # Run tests in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(test) for test in tests]

            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                try:
                    result = future.result(timeout=15)
                    print(f"✅ Test {i+1} completed: {result}")
                except Exception as e:
                    print(f"❌ Test {i+1} failed: {e}")

        print("\n📊 RESULTS SUMMARY:")
        print("="*40)

        if self.results:
            for source, price in self.results.items():
                print(f"{source:20}: ${price:,.2f}")

            # Find most recent/highest confidence source
            if 'yahoo_NQ=F' in self.results:
                best_price = self.results['yahoo_NQ=F']
                best_source = 'yahoo_NQ=F'
            elif self.results:
                best_source = list(self.results.keys())[0]
                best_price = self.results[best_source]
            else:
                best_price = None
                best_source = None

            if best_price:
                print(f"\n🎯 BEST LIVE PRICE: ${best_price:,.2f} from {best_source}")

                # Send one more time to ensure verifier gets it
                self.send_to_verifier(best_price, f'{best_source}_final')

        else:
            print("❌ No live data sources found")

        return self.results

def main():
    """Main execution"""
    hunter = LiveDataHunter()

    print(f"🕐 Starting hunt at {datetime.now().strftime('%H:%M:%S')}")

    results = hunter.run_all_tests()

    print(f"\n🕐 Hunt completed at {datetime.now().strftime('%H:%M:%S')}")

    if results:
        print("✅ SUCCESS: Found live data sources!")

        # Check verification status
        try:
            response = requests.get("http://localhost:8083/api/status")
            if response.status_code == 200:
                status = response.json()
                print(f"\n🔍 Verification Status: {status['message']}")
                if status['is_live']:
                    print("🎉 LIVE DATA VERIFIED!")
                else:
                    print("⚠️ Data not yet verified as live")
        except:
            print("⚠️ Could not check verification status")
    else:
        print("❌ No live data sources found")

if __name__ == "__main__":
    main()
