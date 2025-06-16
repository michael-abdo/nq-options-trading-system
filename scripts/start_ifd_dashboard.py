#!/usr/bin/env python3
"""
Launch Enhanced IFD Dashboard
Quick launcher for the NQ 5-minute chart with IFD v3.0 integration
"""

import sys
import os
import argparse

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from nq_5m_dash_app_ifd import NQDashAppIFD

def main():
    """Launch the IFD dashboard"""
    parser = argparse.ArgumentParser(description='Launch NQ Futures Dashboard with IFD v3.0')
    parser.add_argument('--symbol', default='NQM5', help='Contract symbol (default: NQM5)')
    parser.add_argument('--hours', type=int, default=4, help='Hours of data to display (default: 4)')
    parser.add_argument('--update', type=int, default=30, help='Update interval in seconds (default: 30)')
    parser.add_argument('--port', type=int, default=8050, help='Port to run on (default: 8050)')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')

    args = parser.parse_args()

    print("🚀 Launching Enhanced NQ Futures Dashboard with IFD v3.0")
    print("=" * 60)
    print(f"📊 Symbol: {args.symbol}")
    print(f"⏰ Time Range: {args.hours} hours")
    print(f"🔄 Update Interval: {args.update} seconds")
    print(f"🌐 Port: {args.port}")
    print(f"🎯 URL: http://127.0.0.1:{args.port}")
    print("=" * 60)
    print()
    print("📋 Available IFD Configurations:")
    print("   • Default: Standard chart without IFD signals")
    print("   • IFD Enabled: Basic IFD signals with 70% confidence threshold")
    print("   • IFD Advanced: Enhanced IFD with background highlighting")
    print("   • IFD Minimal: Performance-optimized with 80% confidence threshold")
    print()
    print("🎮 Controls:")
    print("   • Use the dropdown to switch between IFD configurations")
    print("   • Adjust symbol and time range as needed")
    print("   • Click 'Reset Chart' to refresh data")
    print()
    print("⏰ Note: Market data is only available during trading hours")
    print("   • Futures: Sunday 6:00 PM - Friday 5:00 PM ET")
    print("   • Regular: Monday 9:30 AM - Friday 4:00 PM ET")
    print()

    # Create and run the dashboard
    try:
        app = NQDashAppIFD(
            symbol=args.symbol,
            hours=args.hours,
            update_interval=args.update,
            port=args.port
        )

        print("🌐 Starting dashboard... Browser will open automatically")
        print("Press Ctrl+C to stop the dashboard")
        print()

        app.run(debug=args.debug, open_browser=True)

    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
