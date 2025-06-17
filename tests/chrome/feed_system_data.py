#!/usr/bin/env python3
"""
Feed System Data to Live Verification
Connects your trading system data to the live verification system
"""

import sys
import os
import time
import requests
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def feed_databento_data():
    """Get current NQ price from your Databento system and verify it's live"""

    try:
        # Import your Databento provider
        from scripts.databento_5m_provider import Databento5MinuteProvider

        print("📊 Getting current NQ price from Databento...")

        # Initialize provider
        provider = Databento5MinuteProvider()

        # Get latest 1-minute bar (most recent data)
        from datetime import timezone, timedelta
        end_time = datetime.now(timezone.utc) - timedelta(minutes=5)  # Account for delay
        start_time = end_time - timedelta(minutes=1)

        # Fetch data
        bars = provider.fetch_bars('NQ.c.0', start_time, end_time)

        if bars and len(bars) > 0:
            latest_bar = bars.iloc[-1]
            current_price = latest_bar['close']
            timestamp = latest_bar.name

            print(f"✅ Got Databento price: ${current_price:,.2f} at {timestamp}")

            # Send to verification system
            send_to_verifier(current_price, 'databento')

            return current_price
        else:
            print("❌ No Databento data available")
            return None

    except Exception as e:
        print(f"❌ Error getting Databento data: {e}")
        return None

def send_to_verifier(price, source='system'):
    """Send price data to verification system"""
    try:
        response = requests.post('http://localhost:8083/api/system-data',
                               json={'price': price, 'source': source})
        if response.status_code == 200:
            print(f"✅ Sent {source} data to verifier: ${price:,.2f}")
        else:
            print(f"❌ Failed to send to verifier: {response.status_code}")
    except Exception as e:
        print(f"❌ Error sending to verifier: {e}")

def get_verification_status():
    """Get current verification status"""
    try:
        response = requests.get('http://localhost:8083/api/status')
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except:
        return None

def continuous_verification():
    """Continuously feed system data and check verification"""
    print("🔄 Starting continuous live data verification...")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking data freshness...")

            # Get system data
            price = feed_databento_data()

            # Check verification status
            status = get_verification_status()
            if status:
                if status['is_live']:
                    print("✅ VERIFICATION: Data is LIVE!")
                else:
                    print(f"❌ VERIFICATION: {status['message']}")

            print("⏳ Waiting 30 seconds...")
            time.sleep(30)

    except KeyboardInterrupt:
        print("\n\n👋 Stopping verification feed")

def manual_test():
    """Manual test with simulated data"""
    print("🧪 Manual Test Mode")
    print("Sending simulated NQ prices to test verification...")

    # Simulate some price updates
    test_prices = [21930.50, 21931.25, 21929.75, 21932.00]

    for price in test_prices:
        print(f"\n📊 Sending test price: ${price:,.2f}")
        send_to_verifier(price, 'test_data')
        time.sleep(2)

        # Check status
        status = get_verification_status()
        if status:
            print(f"   Status: {status['message']}")

def main():
    """Main menu for data verification"""
    print("🔍 Live Data Verification Feed")
    print("="*50)

    while True:
        print("\nOptions:")
        print("1. Test Databento connection")
        print("2. Start continuous verification")
        print("3. Manual test with simulated data")
        print("4. Check verification status")
        print("5. Exit")

        choice = input("\nSelect option (1-5): ").strip()

        if choice == '1':
            print("\n📊 Testing Databento connection...")
            price = feed_databento_data()
            if price:
                print(f"✅ Successfully got price: ${price:,.2f}")

        elif choice == '2':
            continuous_verification()

        elif choice == '3':
            manual_test()

        elif choice == '4':
            print("\n🔍 Checking verification status...")
            status = get_verification_status()
            if status:
                print(f"Status: {status['status']}")
                print(f"Message: {status['message']}")
                if 'tradovate_price' in status:
                    print(f"Tradovate: ${status['tradovate_price']:,.2f}")
                    print(f"System: ${status['system_price']:,.2f}")
            else:
                print("❌ Cannot connect to verification system")

        elif choice == '5':
            print("👋 Exiting")
            break

        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main()
