#!/usr/bin/env python3
"""
Automatically capture Tradovate data using Chrome Remote Debugging
"""

import asyncio
import websockets
import json
import requests
from datetime import datetime
import time

class TradovateAutoCapture:
    def __init__(self, chrome_debug_port=9222):
        self.debug_port = chrome_debug_port
        self.base_url = f"http://localhost:{chrome_debug_port}"
        self.ws_url = None
        self.tab_id = None

    def find_tradovate_tab(self):
        """Find the Tradovate tab in Chrome"""
        try:
            response = requests.get(f"{self.base_url}/json")
            tabs = response.json()

            for tab in tabs:
                if 'trader.tradovate.com' in tab.get('url', ''):
                    self.tab_id = tab['id']
                    self.ws_url = tab['webSocketDebuggerUrl']
                    print(f"✅ Found Tradovate tab: {tab['title']}")
                    return True

            print("❌ Tradovate tab not found")
            return False

        except Exception as e:
            print(f"❌ Error connecting to Chrome: {e}")
            return False

    async def extract_trading_data(self):
        """Extract trading data from Tradovate DOM"""
        if not self.ws_url:
            return None

        try:
            async with websockets.connect(self.ws_url) as ws:
                # Enable Runtime
                await ws.send(json.dumps({
                    "id": 1,
                    "method": "Runtime.enable"
                }))

                # JavaScript to extract data
                js_code = """
                (() => {
                    const container = document.querySelector('.gm-scroll-view');
                    if (!container) return null;

                    // Get symbol
                    const symbolElem = container.querySelector('.contract-symbol span');
                    const symbol = symbolElem ? symbolElem.textContent.trim() : 'NQ';

                    // Get LAST price
                    const lastPriceElem = container.querySelector('.last-price-info .number');
                    const lastPrice = lastPriceElem ? parseFloat(lastPriceElem.textContent.replace(/,/g, '')) : null;

                    // Get BID and ASK
                    const infoColumns = container.querySelectorAll('.info-column');
                    let bidPrice = null;
                    let askPrice = null;

                    infoColumns.forEach(column => {
                        const label = column.querySelector('small.text-muted');
                        if (label) {
                            if (label.textContent.trim() === 'BID') {
                                const priceElem = column.querySelector('.number');
                                bidPrice = priceElem ? parseFloat(priceElem.textContent.replace(/,/g, '')) : null;
                            } else if (label.textContent.trim() === 'ASK') {
                                const priceElem = column.querySelector('.number');
                                askPrice = priceElem ? parseFloat(priceElem.textContent.replace(/,/g, '')) : null;
                            }
                        }
                    });

                    return {
                        symbol: symbol,
                        lastPrice: lastPrice,
                        bidPrice: bidPrice,
                        askPrice: askPrice,
                        midPrice: bidPrice && askPrice ? (bidPrice + askPrice) / 2 : lastPrice,
                        timestamp: new Date().toISOString()
                    };
                })()
                """

                # Execute JavaScript
                await ws.send(json.dumps({
                    "id": 2,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": js_code,
                        "returnByValue": True
                    }
                }))

                # Get result
                while True:
                    response = await ws.recv()
                    data = json.loads(response)

                    if data.get('id') == 2:
                        if 'result' in data:
                            result = data['result'].get('result', {})
                            if result.get('type') == 'object' and 'value' in result:
                                return result['value']
                        break

        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            return None

    def send_to_verifier(self, trading_data):
        """Send Tradovate data to verification system"""
        if not trading_data or not trading_data.get('lastPrice'):
            return False

        try:
            # Prepare data for verifier
            price = trading_data.get('midPrice') or trading_data.get('lastPrice')

            payload = {
                'timestamp': trading_data['timestamp'],
                'symbol': trading_data['symbol'],
                'price': price,
                'source': 'tradovate_auto'
            }

            # Send as Tradovate reference data
            response = requests.post(
                'http://localhost:8083/api/tradovate-data',
                json=payload,
                timeout=2
            )

            if response.status_code == 200:
                print(f"✅ Sent Tradovate reference: ${price:,.2f}")
                return True
            else:
                print(f"❌ Failed to send: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error sending to verifier: {e}")
            return False

    async def continuous_capture(self, interval=5):
        """Continuously capture and send Tradovate data"""
        print("🔄 Starting continuous Tradovate capture...")
        print(f"   Capturing every {interval} seconds")
        print("   Press Ctrl+C to stop\n")

        capture_count = 0

        try:
            while True:
                # Extract data
                data = await self.extract_trading_data()

                if data:
                    capture_count += 1
                    timestamp = datetime.now().strftime('%H:%M:%S')

                    print(f"[{timestamp}] Capture #{capture_count}")
                    print(f"  Symbol: {data['symbol']}")
                    print(f"  Last: ${data['lastPrice']:,.2f}")

                    if data.get('bidPrice') and data.get('askPrice'):
                        print(f"  Bid/Ask: ${data['bidPrice']:,.2f} / ${data['askPrice']:,.2f}")
                        print(f"  Mid: ${data['midPrice']:,.2f}")

                    # Send to verifier
                    if self.send_to_verifier(data):
                        # Check verification status
                        try:
                            resp = requests.get('http://localhost:8083/api/status')
                            if resp.status_code == 200:
                                status = resp.json()
                                if status['is_live']:
                                    print("  🎉 LIVE DATA VERIFIED!")
                                else:
                                    print(f"  ⏳ Time diff: {status['time_diff']:.1f}s")
                        except:
                            pass
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Could not extract data")

                # Wait for next capture
                await asyncio.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n👋 Stopped continuous capture")

async def main():
    """Main execution"""
    print("🚀 TRADOVATE AUTO-CAPTURE SYSTEM")
    print("="*50)

    capture = TradovateAutoCapture()

    # Find Tradovate tab
    if not capture.find_tradovate_tab():
        print("\n⚠️  Please open Tradovate in Chrome with remote debugging:")
        print("   1. Close Chrome completely")
        print("   2. Run: open -a 'Google Chrome' --args --remote-debugging-port=9222")
        print("   3. Navigate to https://trader.tradovate.com")
        print("   4. Run this script again")
        return

    # Run continuous capture
    await capture.continuous_capture(interval=5)

if __name__ == "__main__":
    asyncio.run(main())
