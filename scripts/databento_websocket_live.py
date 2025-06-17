#!/usr/bin/env python3
"""
Databento WebSocket Live Data Connection
Attempting to connect to Databento's live WebSocket feed
"""

import asyncio
import websockets
import json
import os
from datetime import datetime
import requests
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DatabentoLiveWebSocket:
    def __init__(self):
        self.api_key = os.getenv('DATABENTO_API_KEY')
        self.ws_url = "wss://api.databento.com:13000"
        self.ws = None

    async def authenticate(self):
        """Try different authentication methods"""
        auth_methods = [
            # Method 1: API key in header
            {
                "type": "auth",
                "api_key": self.api_key
            },
            # Method 2: Login message
            {
                "action": "login",
                "key": self.api_key
            },
            # Method 3: Subscribe with auth
            {
                "action": "subscribe",
                "api_key": self.api_key,
                "symbols": ["NQ.c.0"],
                "schema": "mbp-1"
            }
        ]

        for i, auth in enumerate(auth_methods, 1):
            try:
                print(f"🔐 Trying authentication method {i}...")
                await self.ws.send(json.dumps(auth))

                # Wait for response
                response = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
                print(f"✅ Auth method {i} response: {response}")

                # Check if authentication was successful
                resp_data = json.loads(response)
                if resp_data.get('status') == 'ok' or 'error' not in resp_data:
                    print(f"✅ Authentication successful with method {i}")
                    return True

            except Exception as e:
                print(f"❌ Auth method {i} failed: {e}")
                continue

        return False

    async def subscribe_to_nq(self):
        """Subscribe to NQ live data"""
        subscribe_messages = [
            # Standard subscription
            {
                "action": "subscribe",
                "symbols": ["NQ.c.0"],
                "schema": "mbp-1",
                "start": "live"
            },
            # MBO subscription
            {
                "action": "subscribe",
                "symbols": ["NQ.c.0"],
                "schema": "mbo",
                "start": "live"
            },
            # Trade subscription
            {
                "action": "subscribe",
                "symbols": ["NQ.c.0"],
                "schema": "trades",
                "start": "live"
            }
        ]

        for sub in subscribe_messages:
            try:
                print(f"📡 Subscribing to {sub['schema']} data...")
                await self.ws.send(json.dumps(sub))

                response = await asyncio.wait_for(self.ws.recv(), timeout=3.0)
                print(f"📊 Subscription response: {response}")

            except Exception as e:
                print(f"❌ Subscription failed: {e}")

    async def connect_and_stream(self):
        """Main connection and streaming loop"""
        try:
            print(f"🔌 Connecting to {self.ws_url}...")

            # Try connecting with different headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Key": self.api_key,
                "User-Agent": "databento-python/0.35.0"
            }

            async with websockets.connect(
                self.ws_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                self.ws = websocket
                print("✅ WebSocket connected!")

                # Try authentication
                authenticated = await self.authenticate()

                if authenticated:
                    # Try subscribing
                    await self.subscribe_to_nq()

                    # Listen for data
                    print("🎧 Listening for live data...")
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            print(f"📊 Live data: {data}")

                            # Send to verification system
                            await self.send_to_verifier(data)

                        except json.JSONDecodeError:
                            print(f"📄 Raw message: {message}")

                else:
                    print("❌ Could not authenticate - trying to listen anyway...")

                    # Listen for any data without auth
                    async for message in websocket:
                        print(f"📊 Message (no auth): {message}")

        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")
            return False

    async def send_to_verifier(self, data):
        """Send live data to verification system"""
        try:
            # Extract price from various possible formats
            price = None

            if isinstance(data, dict):
                # Look for price fields
                for field in ['price', 'last', 'close', 'bid', 'ask']:
                    if field in data:
                        price = float(data[field])
                        break

                # Look in nested structures
                if not price and 'levels' in data:
                    levels = data['levels']
                    if levels and len(levels) > 0:
                        price = float(levels[0].get('price', 0))

            if price and price > 0:
                # Send to verification system via HTTP
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        'http://localhost:8083/api/system-data',
                        json={'price': price, 'source': 'databento_live_ws'}
                    )
                print(f"✅ Sent live price to verifier: ${price:,.2f}")

        except Exception as e:
            print(f"❌ Failed to send to verifier: {e}")

def check_api_key():
    """Check if API key is available"""
    api_key = os.getenv('DATABENTO_API_KEY')
    if not api_key:
        print("❌ DATABENTO_API_KEY not found in environment")
        print("Please set your API key:")
        print("export DATABENTO_API_KEY='your_key_here'")
        return False

    print(f"✅ API key found: {api_key[:8]}...")
    return True

async def main():
    """Main function"""
    print("🚀 ITERATION 25: Databento Live WebSocket Connection")
    print("="*60)

    if not check_api_key():
        return

    # Try connecting to live WebSocket
    ws_client = DatabentoLiveWebSocket()

    print("🎯 Attempting aggressive WebSocket connection...")
    await ws_client.connect_and_stream()

if __name__ == "__main__":
    asyncio.run(main())
