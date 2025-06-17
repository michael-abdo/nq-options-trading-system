#!/usr/bin/env python3
"""
Compare NQ prices from different sources
"""

import asyncio
import websockets
import json
import databento as db
import os
import time
from datetime import datetime

async def get_tradovate_price():
    """Get current NQ price from Tradovate"""
    ws_url = 'ws://localhost:9222/devtools/page/6B935C27F5DC7E8EBF6326922B703A1E'

    try:
        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps({'id': 1, 'method': 'Runtime.enable'}))
            await ws.send(json.dumps({
                'id': 2, 'method': 'Runtime.evaluate',
                'params': {
                    'expression': 'document.querySelector(".last-price-info .number")?.textContent',
                    'returnByValue': True
                }
            }))

            while True:
                resp = await ws.recv()
                data = json.loads(resp)
                if data.get('id') == 2:
                    result = data.get('result', {}).get('result', {}).get('value')
                    if result and result != 'not found':
                        return float(result.replace(',', ''))
                    break

    except Exception as e:
        print(f"Tradovate error: {e}")

    return None

def get_databento_price():
    """Get current NQ price from Databento"""
    client = db.Live(key=os.getenv('DATABENTO_API_KEY'))

    prices = []

    def on_data(record):
        # Look for trade records
        if hasattr(record, 'price') and hasattr(record, 'size'):
            price = float(record.price) / 1e9
            if 20000 < price < 25000:  # Reasonable NQ range
                prices.append(price)

        # Look for quote records
        elif hasattr(record, 'bid_px_00') and hasattr(record, 'ask_px_00'):
            if record.bid_px_00 and record.ask_px_00:
                bid = float(record.bid_px_00) / 1e9
                ask = float(record.ask_px_00) / 1e9
                if 20000 < bid < 25000 and 20000 < ask < 25000:
                    mid = (bid + ask) / 2
                    prices.append(mid)

    client.add_callback(on_data)

    try:
        client.subscribe(dataset='GLBX.MDP3', symbols=['NQ.c.0'], schema='trades')
        client.subscribe(dataset='GLBX.MDP3', symbols=['NQ.c.0'], schema='mbp-1')
        client.start()

        # Wait for data
        time.sleep(8)

        client.stop()

        return prices[-1] if prices else None

    except Exception as e:
        print(f"Databento error: {e}")
        return None

async def main():
    print("🔍 NQ PRICE COMPARISON")
    print("=" * 40)
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Get Tradovate price
    print("📊 Getting Tradovate NQ price...")
    tradovate_price = await get_tradovate_price()

    if tradovate_price:
        print(f"   Tradovate: ${tradovate_price:,.2f}")
    else:
        print("   Tradovate: Not available")

    # Get Databento price
    print("\n📊 Getting Databento NQ price...")
    databento_price = get_databento_price()

    if databento_price:
        print(f"   Databento: ${databento_price:,.2f}")
    else:
        print("   Databento: Not available")

    # Compare
    print("\n🔬 COMPARISON:")
    print("-" * 30)

    if tradovate_price and databento_price:
        difference = abs(tradovate_price - databento_price)
        percent_diff = (difference / tradovate_price) * 100

        print(f"Tradovate:  ${tradovate_price:,.2f}")
        print(f"Databento:  ${databento_price:,.2f}")
        print(f"Difference: ${difference:.2f} ({percent_diff:.3f}%)")

        if difference < 1.0:
            print("✅ VERY CLOSE - Same market data!")
        elif difference < 5.0:
            print("✅ CLOSE - Minor difference")
        elif difference < 20.0:
            print("⚠️  MODERATE - Possibly different contracts or timing")
        else:
            print("❌ LARGE - Different data sources")

        # Check if they're the same contract
        if difference < 5.0:
            print("\n💡 Analysis: Both sources showing same NQ contract")
            print("   Difference likely due to:")
            print("   - Bid/ask spread vs last trade price")
            print("   - Microsecond timing differences")
            print("   - Different data feeds (but same underlying market)")
        else:
            print("\n💡 Analysis: Sources might be showing:")
            print("   - Different contract months (front month vs continuous)")
            print("   - Different market sessions")
            print("   - One showing futures, other showing cash/ETF")

    else:
        print("❌ Could not compare - missing data from one or both sources")

if __name__ == "__main__":
    asyncio.run(main())
