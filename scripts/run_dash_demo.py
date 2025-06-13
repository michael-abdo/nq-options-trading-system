#!/usr/bin/env python3
"""
Simple demo runner for the Dash app
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nq_5m_dash_app import NQDashApp
import time

def main():
    """Run a short demo of the Dash app"""
    print("🚀 Starting NQ 5-Minute Real-Time Chart Dashboard")
    print("=" * 60)
    print()
    print("Features:")
    print("✅ Real-time data updates every 30 seconds")
    print("✅ Interactive candlestick charts with volume")
    print("✅ Moving averages (MA20, MA50)")
    print("✅ Auto-refreshing browser display")
    print("✅ Symbol and timeframe controls")
    print("✅ Live price and statistics display")
    print()
    print("Controls:")
    print("🔹 Change symbol (NQM5, NQZ5, etc.)")
    print("🔹 Adjust time range (1h, 2h, 4h, 8h, 1d)")
    print("🔹 Reset chart data")
    print()
    print("💡 The dashboard will open automatically in your browser")
    print("🛑 Press Ctrl+C to stop the server")
    print()

    try:
        # Create app with reasonable settings for demo
        app = NQDashApp(
            symbol="NQM5",
            hours=4,
            update_interval=30,  # 30 second updates
            port=8050
        )

        # Run the app
        app.run(debug=False)

    except KeyboardInterrupt:
        print("\n\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"\n❌ Error running dashboard: {e}")

if __name__ == "__main__":
    main()
