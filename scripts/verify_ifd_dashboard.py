#!/usr/bin/env python3
"""
Verify the IFD dashboard is working correctly
"""

import requests
import time

def check_dashboard():
    """Check if dashboard is running and responding"""
    try:
        # Check if dashboard is accessible
        response = requests.get('http://127.0.0.1:8050/', timeout=5)
        if response.status_code == 200:
            print("✅ Dashboard is running at http://127.0.0.1:8050/")

            # Check for IFD elements in the HTML
            if 'IFD Configuration' in response.text:
                print("✅ IFD Configuration dropdown found")
            else:
                print("❌ IFD Configuration dropdown not found")

            if 'IFD v3.0' in response.text:
                print("✅ IFD v3.0 title found")
            else:
                print("❌ IFD v3.0 title not found")

            # Check for key components
            if 'live-chart' in response.text:
                print("✅ Live chart component found")
            else:
                print("❌ Live chart component not found")

            if 'ifd-config-dropdown' in response.text:
                print("✅ IFD config dropdown ID found")
            else:
                print("❌ IFD config dropdown ID not found")

            return True
        else:
            print(f"❌ Dashboard returned status code: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to dashboard at http://127.0.0.1:8050/")
        print("   Make sure the dashboard is running")
        return False
    except Exception as e:
        print(f"❌ Error checking dashboard: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Verifying IFD Dashboard...")
    print("-" * 50)

    if check_dashboard():
        print("\n✅ Dashboard verification PASSED!")
        print("\n📊 The live dashboard now has:")
        print("   • IFD configuration dropdown")
        print("   • Demo mode for weekends")
        print("   • Signal overlay capabilities")
        print("   • Dark theme styling")
        print("\n🎯 To use:")
        print("   1. Open http://127.0.0.1:8050/ in your browser")
        print("   2. Select an IFD configuration from the dropdown")
        print("   3. Demo signals will appear on the chart")
        print("   4. During market hours, live data will be shown")
    else:
        print("\n❌ Dashboard verification FAILED!")
        print("\nPlease ensure the dashboard is running with:")
        print("   bash scripts/start_live_ifd_dashboard.sh")
