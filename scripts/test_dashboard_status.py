#!/usr/bin/env python3
"""
Test Dashboard Status - Check if dashboard is working
"""

import requests
import time
import json

def check_dashboard(port=8050, max_retries=5):
    """Check if dashboard is running and responding"""

    print(f"🔍 Checking dashboard at http://127.0.0.1:{port}/")
    print("=" * 50)

    # Give dashboard time to start
    time.sleep(2)

    for attempt in range(max_retries):
        try:
            # Try to connect to dashboard
            response = requests.get(f"http://127.0.0.1:{port}/", timeout=5)

            if response.status_code == 200:
                print("✅ Dashboard is running!")
                print(f"   Status Code: {response.status_code}")
                print(f"   Content Length: {len(response.text)} characters")

                # Check if it's the IFD dashboard
                if "IFD" in response.text or "ifd" in response.text:
                    print("✅ IFD integration detected in dashboard")
                else:
                    print("⚠️  IFD integration not detected")

                # Check for key elements
                elements = {
                    "Dash app": "<!DOCTYPE html>" in response.text,
                    "Chart element": "live-chart" in response.text or "chart" in response.text,
                    "IFD dropdown": "ifd-config-dropdown" in response.text,
                    "Status display": "price-display" in response.text or "status" in response.text
                }

                print("\n📊 Dashboard Elements:")
                for element, present in elements.items():
                    status = "✅" if present else "❌"
                    print(f"   {status} {element}")

                return True

        except requests.ConnectionError:
            print(f"⏳ Attempt {attempt + 1}/{max_retries}: Dashboard not ready yet...")
            time.sleep(2)
        except Exception as e:
            print(f"❌ Error checking dashboard: {e}")
            return False

    print("❌ Dashboard is not responding")
    print("   Make sure it's running with: python scripts/start_ifd_dashboard.py")
    return False

def main():
    print("🎯 Dashboard Status Check")
    print()

    # Check if dashboard is running
    if check_dashboard():
        print("\n✅ Dashboard is working!")
        print("\n📱 Open your browser to: http://127.0.0.1:8050/")
        print("\n🎮 What you should see:")
        print("   • Sample candlestick chart (since markets are closed)")
        print("   • IFD configuration dropdown")
        print("   • Demo IFD signal overlays when IFD is enabled")
        print("   • Dark theme with green/red candles")
        print("\n💡 Try switching between IFD configurations:")
        print("   • Default: No signals")
        print("   • IFD Enabled: Basic signals")
        print("   • IFD Advanced: Enhanced signals with background")
        print("   • IFD Minimal: High-confidence signals only")
    else:
        print("\n❌ Dashboard is not running")
        print("\n🔧 To start it:")
        print("   python scripts/start_ifd_dashboard.py")

if __name__ == "__main__":
    main()
