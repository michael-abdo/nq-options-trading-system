#!/usr/bin/env python3
"""
Yahoo Finance NQ Live Data Test
Direct approach to get live NQ data from Yahoo Finance
"""

import requests
import json
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_yahoo_nq_price():
    """Get live NQ price from Yahoo Finance"""

    # NQ futures symbols to try
    symbols = ['NQ=F', 'NQZ24.CME', 'NQU24.CME', '/NQ']

    for symbol in symbols:
        try:
            print(f"🔍 Trying Yahoo symbol: {symbol}")

            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {
                'interval': '1m',
                'range': '1d',
                'includePrePost': 'true'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            print(f"Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                if 'chart' in data and data['chart']['result']:
                    result = data['chart']['result'][0]
                    meta = result.get('meta', {})

                    print(f"📊 Meta data keys: {list(meta.keys())}")

                    # Try different price fields
                    price_fields = [
                        'regularMarketPrice',
                        'previousClose',
                        'chartPreviousClose',
                        'currentTradingPeriod'
                    ]

                    for field in price_fields:
                        if field in meta:
                            price = meta[field]
                            if isinstance(price, (int, float)) and price > 0:
                                print(f"✅ Yahoo {symbol} - {field}: ${price:,.2f}")

                                # Send to verifier
                                send_to_verifier(price, f'yahoo_{symbol}')
                                return price

                    # Try timestamp data
                    if 'timestamp' in result and 'indicators' in result:
                        timestamps = result['timestamp']
                        indicators = result['indicators']

                        if 'quote' in indicators and indicators['quote']:
                            quote = indicators['quote'][0]
                            if 'close' in quote and quote['close']:
                                prices = quote['close']
                                # Get the last non-null price
                                for price in reversed(prices):
                                    if price is not None:
                                        print(f"✅ Yahoo {symbol} - latest close: ${price:,.2f}")
                                        send_to_verifier(price, f'yahoo_{symbol}_close')
                                        return price

                print(f"❌ No price found in Yahoo response for {symbol}")
                print(f"Response preview: {str(data)[:500]}...")

            else:
                print(f"❌ Yahoo API error for {symbol}: {response.status_code}")

        except Exception as e:
            print(f"❌ Error with {symbol}: {e}")

    return None

def send_to_verifier(price, source):
    """Send price to verification system"""
    try:
        response = requests.post(
            'http://localhost:8083/api/system-data',
            json={'price': price, 'source': source},
            timeout=3
        )
        if response.status_code == 200:
            print(f"✅ Sent {source} data to verifier: ${price:,.2f}")
            return True
        else:
            print(f"❌ Failed to send to verifier: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Verifier error: {e}")
        return False

def get_verification_status():
    """Check verification status"""
    try:
        response = requests.get('http://localhost:8083/api/status')
        if response.status_code == 200:
            status = response.json()
            print(f"\n🔍 Verification Status: {status['message']}")
            if status['is_live']:
                print("🎉 LIVE DATA VERIFIED!")
            else:
                print("⚠️ Data not verified as live")
            return status
        else:
            print("❌ Cannot get verification status")
            return None
    except Exception as e:
        print(f"❌ Verification check error: {e}")
        return None

def main():
    """Main function"""
    print("🚀 Yahoo Finance NQ Live Data Test")
    print("="*50)

    print(f"🕐 Testing at {datetime.now().strftime('%H:%M:%S')}")

    # Get Yahoo price
    price = get_yahoo_nq_price()

    if price:
        print(f"\n✅ SUCCESS! Got live price: ${price:,.2f}")

        # Check verification
        get_verification_status()

    else:
        print("\n❌ Could not get live price from Yahoo Finance")

        # Try a simple alternative
        print("\n🔄 Trying alternative approach...")
        try_alternative_yahoo()

def try_alternative_yahoo():
    """Try alternative Yahoo Finance endpoint"""
    try:
        # Try direct quote endpoint
        url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=NQ=F"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if 'quoteResponse' in data and 'result' in data['quoteResponse']:
                results = data['quoteResponse']['result']
                if results:
                    quote = results[0]

                    print(f"📊 Quote fields: {list(quote.keys())}")

                    # Look for price fields
                    price_fields = ['regularMarketPrice', 'ask', 'bid', 'previousClose']

                    for field in price_fields:
                        if field in quote:
                            price = quote[field]
                            if price and price > 0:
                                print(f"✅ Alternative Yahoo - {field}: ${price:,.2f}")
                                send_to_verifier(price, f'yahoo_alt_{field}')
                                return price

        print("❌ Alternative Yahoo approach failed")
        return None

    except Exception as e:
        print(f"❌ Alternative Yahoo error: {e}")
        return None

if __name__ == "__main__":
    main()
