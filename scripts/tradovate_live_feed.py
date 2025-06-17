#!/usr/bin/env python3
"""
Tradovate Live Feed - Automatic data extraction
"""

import asyncio
import websockets
import json
import requests
from datetime import datetime
import time

async def get_tradovate_data():
    """Extract live data from Tradovate"""
    ws_url = 'ws://localhost:9222/devtools/page/6B935C27F5DC7E8EBF6326922B703A1E'

    try:
        async with websockets.connect(ws_url) as ws:
            # Enable Runtime
            await ws.send(json.dumps({
                'id': 1,
                'method': 'Runtime.enable'
            }))

            # JavaScript to extract all data
            js_code = """
            (() => {
                const lastElem = document.querySelector('.last-price-info .number');
                const lastPrice = lastElem ? parseFloat(lastElem.textContent.replace(/,/g, '')) : null;

                // Get bid/ask
                let bidPrice = null;
                let askPrice = null;

                const infoColumns = document.querySelectorAll('.info-column');
                infoColumns.forEach(col => {
                    const label = col.querySelector('small.text-muted');
                    if (label) {
                        const text = label.textContent.trim();
                        const priceElem = col.querySelector('.number');
                        if (text === 'BID' && priceElem) {
                            bidPrice = parseFloat(priceElem.textContent.replace(/,/g, ''));
                        } else if (text === 'ASK' && priceElem) {
                            askPrice = parseFloat(priceElem.textContent.replace(/,/g, ''));
                        }
                    }
                });

                return {
                    lastPrice: lastPrice,
                    bidPrice: bidPrice,
                    askPrice: askPrice,
                    midPrice: bidPrice && askPrice ? (bidPrice + askPrice) / 2 : lastPrice,
                    timestamp: new Date().toISOString()
                };
            })()
            """

            await ws.send(json.dumps({
                'id': 2,
                'method': 'Runtime.evaluate',
                'params': {
                    'expression': js_code,
                    'returnByValue': True
                }
            }))

            # Get response
            while True:
                resp = await ws.recv()
                data = json.loads(resp)
                if data.get('id') == 2:
                    result = data.get('result', {}).get('result', {}).get('value')
                    return result

    except Exception as e:
        print(f'Error: {e}')
        return None

def send_to_verifier(price):
    """Send Tradovate price as reference data"""
    try:
        payload = {
            'timestamp': datetime.now().isoformat(),
            'symbol': 'NQ',
            'price': price,
            'source': 'tradovate_live'
        }

        response = requests.post(
            'http://localhost:8083/api/tradovate-data',
            json=payload,
            timeout=2
        )

        if response.status_code == 200:
            return True
    except:
        pass
    return False

async def continuous_feed():
    """Continuously feed Tradovate data to verifier"""
    print("🚀 TRADOVATE LIVE FEED")
    print("="*50)
    print("Extracting real-time NQ data from Tradovate")
    print("Sending to verification system...")
    print()

    count = 0
    last_price = None

    while True:
        try:
            # Get data
            data = await get_tradovate_data()

            if data and data.get('lastPrice'):
                count += 1
                price = data['lastPrice']
                timestamp = datetime.now().strftime('%H:%M:%S')

                # Show price change
                if last_price:
                    change = price - last_price
                    arrow = '↑' if change > 0 else '↓' if change < 0 else '='
                    print(f"[{timestamp}] NQ: ${price:,.2f} {arrow} ({change:+.2f})")
                else:
                    print(f"[{timestamp}] NQ: ${price:,.2f}")

                last_price = price

                # Send to verifier
                if send_to_verifier(price):
                    print(f"  ✅ Sent to verifier as reference")

                    # Check verification status
                    try:
                        resp = requests.get('http://localhost:8083/api/status')
                        if resp.status_code == 200:
                            status = resp.json()
                            if status['is_live']:
                                print("  🎉 LIVE DATA VERIFIED!")
                                print(f"  Time diff: {status['time_diff']:.1f}s")
                                print(f"  Price diff: ${status['price_diff']:.2f}")
                    except:
                        pass

                # Show bid/ask if available
                if count % 5 == 0 and data.get('bidPrice') and data.get('askPrice'):
                    print(f"  Bid/Ask: ${data['bidPrice']:,.2f} / ${data['askPrice']:,.2f}")

            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for data...")

            # Wait 3 seconds
            await asyncio.sleep(3)

        except KeyboardInterrupt:
            print("\n\nStopped")
            break
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(continuous_feed())
