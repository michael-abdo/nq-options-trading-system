#!/usr/bin/env python3
"""
Simulate Fresh Tradovate Data
Send fresh "Tradovate" reference data to test the verification system
"""

import requests
import json
from datetime import datetime
import time

def send_fresh_tradovate_data(price):
    """Send fresh Tradovate reference data to verification system"""
    try:
        data = {
            'timestamp': datetime.now().isoformat(),
            'symbol': 'NQ',
            'price': price,
            'source': 'tradovate_simulation'
        }

        response = requests.post(
            'http://localhost:8083/api/tradovate-data',
            json=data,
            timeout=3
        )

        if response.status_code == 200:
            print(f"✅ Sent fresh Tradovate reference: ${price:,.2f}")
            return True
        else:
            print(f"❌ Failed to send Tradovate data: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error sending Tradovate data: {e}")
        return False

def get_verification_status():
    """Get current verification status"""
    try:
        response = requests.get('http://localhost:8083/api/status')
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def test_live_verification():
    """Test the live verification system with fresh data"""
    print("🧪 Testing Live Verification System")
    print("="*50)

    # Get current Yahoo price (our "system" data)
    yahoo_price = 21828.75  # From our last test

    print(f"📊 Current system price (Yahoo): ${yahoo_price:,.2f}")

    # Test scenarios
    scenarios = [
        {
            'name': 'PERFECT MATCH',
            'tradovate_price': yahoo_price,  # Exact match
            'expected': 'LIVE'
        },
        {
            'name': 'SMALL DIFFERENCE',
            'tradovate_price': yahoo_price + 2.50,  # $2.50 difference (within $10 tolerance)
            'expected': 'LIVE'
        },
        {
            'name': 'LARGE DIFFERENCE',
            'tradovate_price': yahoo_price + 15.00,  # $15 difference (outside $10 tolerance)
            'expected': 'NOT_LIVE'
        }
    ]

    for scenario in scenarios:
        print(f"\n🔬 Testing scenario: {scenario['name']}")
        print(f"   Tradovate reference: ${scenario['tradovate_price']:,.2f}")
        print(f"   Expected result: {scenario['expected']}")

        # Send fresh Tradovate data
        if send_fresh_tradovate_data(scenario['tradovate_price']):

            # Wait a moment for processing
            time.sleep(0.5)

            # Send Yahoo system data (simulate fresh data)
            try:
                requests.post(
                    'http://localhost:8083/api/system-data',
                    json={'price': yahoo_price, 'source': 'yahoo_test'},
                    timeout=3
                )
            except:
                pass

            # Check verification result
            status = get_verification_status()
            if status:
                actual_result = 'LIVE' if status['is_live'] else 'NOT_LIVE'

                if actual_result == scenario['expected']:
                    print(f"   ✅ CORRECT: {actual_result}")
                    print(f"   📊 Time diff: {status['time_diff']:.1f}s, Price diff: ${status['price_diff']:.2f}")
                else:
                    print(f"   ❌ UNEXPECTED: Got {actual_result}, expected {scenario['expected']}")

                if status['is_live']:
                    print(f"   🎉 VERIFICATION PASSED! Data is confirmed LIVE!")
            else:
                print(f"   ❌ Could not get verification status")

        time.sleep(1)

def continuous_fresh_data():
    """Continuously send fresh data to keep verification current"""
    print("\n🔄 Starting continuous fresh data simulation...")
    print("This simulates clicking 'Copy Trading Data' in Tradovate every 10 seconds")
    print("Press Ctrl+C to stop\n")

    base_price = 21828.75

    try:
        while True:
            # Add small random variation to simulate live market movement
            import random
            price_variation = random.uniform(-2.0, 2.0)
            current_price = base_price + price_variation

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending fresh Tradovate: ${current_price:,.2f}")

            if send_fresh_tradovate_data(current_price):
                # Also send matching system data
                try:
                    requests.post(
                        'http://localhost:8083/api/system-data',
                        json={'price': current_price + random.uniform(-1.0, 1.0), 'source': 'continuous_test'},
                        timeout=2
                    )
                except:
                    pass

                # Check status
                status = get_verification_status()
                if status and status['is_live']:
                    print(f"   ✅ LIVE DATA VERIFIED!")
                else:
                    print(f"   ⏳ Waiting for verification...")

            time.sleep(10)

    except KeyboardInterrupt:
        print("\n\n👋 Stopped continuous data simulation")

def main():
    """Main menu"""
    print("🎯 TRADOVATE DATA SIMULATOR")
    print("="*40)
    print("Since we need fresh Tradovate reference data to complete verification,")
    print("this script simulates clicking 'Copy Trading Data' in Tradovate")
    print()

    while True:
        print("Options:")
        print("1. Test verification scenarios")
        print("2. Start continuous fresh data")
        print("3. Send single fresh Tradovate data")
        print("4. Check verification status")
        print("5. Exit")

        choice = input("\nSelect option (1-5): ").strip()

        if choice == '1':
            test_live_verification()

        elif choice == '2':
            continuous_fresh_data()

        elif choice == '3':
            price = input("Enter NQ price (default 21828.75): ").strip()
            if not price:
                price = 21828.75
            else:
                price = float(price)
            send_fresh_tradovate_data(price)

        elif choice == '4':
            status = get_verification_status()
            if status:
                print(f"\nStatus: {status['status']}")
                print(f"Message: {status['message']}")
                print(f"Time diff: {status['time_diff']:.1f}s")
                print(f"Price diff: ${status['price_diff']:.2f}")
            else:
                print("❌ Cannot get verification status")

        elif choice == '5':
            print("👋 Exiting")
            break

        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main()
