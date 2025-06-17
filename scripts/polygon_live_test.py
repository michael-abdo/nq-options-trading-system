#!/usr/bin/env python3
"""
Test Polygon.io Live Data as Alternative
Since Databento might require subscription upgrade, try Polygon
"""

import os
import requests
import json
import websockets
import asyncio
from datetime import datetime
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class PolygonLiveTest:
    def __init__(self):
        self.api_key = os.getenv('POLYGON_API_KEY')
        self.base_url = "https://api.polygon.io"

    def test_rest_api(self):
        """Test Polygon REST API for current NQ price"""
        if not self.api_key:
            print("❌ POLYGON_API_KEY not found")
            return None

        try:
            # Get last trade for NQ futures
            url = f"{self.base_url}/v2/last/trade/NQ"
            params = {'apikey': self.api_key}

            print(f"🔍 Testing Polygon REST API: {url}")
            response = requests.get(url, params=params)

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Polygon response: {json.dumps(data, indent=2)}")

                if 'results' in data:
                    price = data['results'].get('p', 0)
                    if price > 0:
                        print(f"📊 Current NQ price from Polygon: ${price:,.2f}")
                        return price

            else:
                print(f"❌ API Error: {response.text}")

        except Exception as e:
            print(f"❌ Polygon REST test failed: {e}")

        return None

    async def test_websocket(self):
        """Test Polygon WebSocket for live data"""
        if not self.api_key:
            print("❌ POLYGON_API_KEY not found")
            return

        ws_url = f"wss://socket.polygon.io/futures?apikey={self.api_key}"

        try:
            print(f"🔌 Connecting to Polygon WebSocket: {ws_url}")

            async with websockets.connect(ws_url) as websocket:
                print("✅ Connected to Polygon WebSocket!")

                # Subscribe to NQ
                subscribe_msg = {
                    "action": "subscribe",
                    "params": "T.NQ"  # NQ trades
                }

                await websocket.send(json.dumps(subscribe_msg))
                print(f"📡 Sent subscription: {subscribe_msg}")

                # Listen for messages
                print("🎧 Listening for live data...")

                timeout_count = 0
                while timeout_count < 10:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        data = json.loads(message)
                        print(f"📊 Polygon live data: {data}")

                        # Send to verifier if it's trade data
                        if isinstance(data, list):
                            for item in data:
                                if item.get('ev') == 'T' and 'p' in item:  # Trade event with price
                                    await self.send_to_verifier(item['p'])

                        timeout_count = 0  # Reset on successful message

                    except asyncio.TimeoutError:
                        timeout_count += 1
                        print(f"⏳ Waiting for data... ({timeout_count}/10)")

                print("⏱️ WebSocket test completed")

        except Exception as e:
            print(f"❌ Polygon WebSocket test failed: {e}")

    async def send_to_verifier(self, price):
        """Send price to verification system"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                await session.post(
                    'http://localhost:8083/api/system-data',
                    json={'price': price, 'source': 'polygon_live'}
                )
            print(f"✅ Sent Polygon price to verifier: ${price:,.2f}")
        except Exception as e:
            print(f"❌ Failed to send to verifier: {e}")

async def main():
    """Test Polygon as live data alternative"""
    print("🚀 Testing Polygon.io Live Data Alternative")
    print("="*50)

    polygon = PolygonLiveTest()

    # Test REST API first
    print("1️⃣ Testing REST API...")
    rest_price = polygon.test_rest_api()

    if rest_price:
        print(f"✅ REST API working - got price: ${rest_price:,.2f}")

    # Test WebSocket
    print("\n2️⃣ Testing WebSocket...")
    await polygon.test_websocket()

if __name__ == "__main__":
    asyncio.run(main())
