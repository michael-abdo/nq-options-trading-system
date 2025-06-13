#!/usr/bin/env python3
"""
TRADING-SAFE Chart Launcher
Guarantees authentic data or fails completely
NO RISK of fake data causing trading losses
"""

import sys
import os
import logging
from datetime import datetime

# Configure logging for trading safety
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'trading_safety_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Launch trading-safe chart with bulletproof authentication"""

    print("🚀 STARTING TRADING-SAFE NQ 5-MINUTE CHART")
    print("=" * 60)
    print("🔐 BULLETPROOF AUTHENTICATION MODE")
    print("🚫 ZERO TOLERANCE FOR FAKE DATA")
    print("=" * 60)

    try:
        # Step 1: Bulletproof authentication test
        print("\n🔐 STEP 1: BULLETPROOF AUTHENTICATION TEST")
        print("-" * 50)

        from databento_auth import DatabentoBulletproofAuth, DatabentoCriticalAuthError

        auth = DatabentoBulletproofAuth()
        api_key = auth.load_and_validate_api_key()

        print(f"✅ API Key Validated: {api_key[:10]}...")
        auth.assert_trading_safe()
        print("✅ SYSTEM CONFIRMED SAFE FOR TRADING")

        # Step 2: Test data provider
        print("\n📊 STEP 2: TESTING TRADING-SAFE DATA PROVIDER")
        print("-" * 50)

        from databento_5m_provider import Databento5MinuteProvider

        provider = Databento5MinuteProvider()
        print("✅ Trading-safe data provider initialized")

        # Test with small data fetch
        print("🧪 Testing live data fetch...")
        df = provider.get_historical_5min_bars(symbol="NQM5", hours_back=1)

        if df.empty:
            raise Exception("No data returned from provider")

        last_price = df['close'].iloc[-1]
        bar_count = len(df)
        time_range = f"{df.index[0]} to {df.index[-1]}"

        print(f"✅ REAL DATA CONFIRMED:")
        print(f"   📈 NQM5 Price: ${last_price:,.2f}")
        print(f"   📊 Bars: {bar_count}")
        print(f"   ⏰ Range: {time_range}")

        # Step 3: Launch chart application
        print("\n🎨 STEP 3: LAUNCHING CHART APPLICATION")
        print("-" * 50)

        import argparse

        # Simple argument parsing for chart type
        parser = argparse.ArgumentParser(description="Trading-Safe Chart Launcher")
        parser.add_argument('--type', choices=['static', 'dashboard'], default='dashboard',
                          help='Chart type: static or dashboard (default: dashboard)')
        parser.add_argument('--symbol', default='NQM5', help='Symbol to chart')
        parser.add_argument('--hours', type=int, default=4, help='Hours of data')

        # Parse args, ignoring unknown ones
        args, unknown = parser.parse_known_args()

        print(f"📊 Chart Type: {args.type}")
        print(f"🎯 Symbol: {args.symbol}")
        print(f"⏰ Hours: {args.hours}")

        if args.type == 'dashboard':
            print("\n🌐 LAUNCHING REAL-TIME DASHBOARD...")
            print("   Dashboard will open automatically in your browser")
            print("   URL: http://localhost:8050")
            print("   Press Ctrl+C to stop")

            from nq_5m_dash_app import NQDashApp

            app = NQDashApp(
                symbol=args.symbol,
                hours=args.hours,
                update_interval=30,
                port=8050
            )

            app.run(debug=False)

        else:  # static
            print(f"\n📈 GENERATING STATIC CHART...")
            output_file = f"outputs/trading_safe_{args.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

            from nq_5m_chart import NQFiveMinuteChart

            chart = NQFiveMinuteChart(
                symbol=args.symbol,
                hours=args.hours,
                update_interval=30
            )

            chart.update_chart()
            filename = chart.save_chart(output_file)

            print(f"✅ Chart saved: {filename}")

    except DatabentoCriticalAuthError as e:
        print(f"\n🚨 CRITICAL AUTHENTICATION FAILURE:")
        print("-" * 50)
        print(str(e))
        print("\n🛑 CHART NOT STARTED FOR TRADING SAFETY")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR:")
        print("-" * 50)
        print(f"Error: {e}")
        print(f"Type: {type(e).__name__}")
        print("\n🛑 CHART NOT STARTED DUE TO ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
