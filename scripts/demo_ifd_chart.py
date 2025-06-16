#!/usr/bin/env python3
"""
Demo IFD Chart Integration
Shows how to use IFD v3.0 signals with 5-minute charts during weekdays
"""

import os
import sys
from datetime import datetime, timedelta
import logging

# Add parent directory for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from scripts.chart_config_manager import ChartConfigManager
from scripts.nq_5m_chart import NQFiveMinuteChart

def demo_ifd_configuration():
    """Demonstrate IFD configuration loading and validation"""
    print("=== IFD Chart Configuration Demo ===")

    config_manager = ChartConfigManager()

    # Show available configurations
    print("\n📋 Available IFD Configurations:")
    configs = ["ifd_enabled", "ifd_advanced", "ifd_minimal"]

    for config_name in configs:
        try:
            config = config_manager.load_config(config_name)
            ifd_config = config.get("indicators", {}).get("ifd_v3", {})

            print(f"\n🔧 {config_name.upper()}:")
            print(f"   Show Signals: {ifd_config.get('show_signals', False)}")
            print(f"   Min Confidence: {ifd_config.get('min_confidence_display', 0.0)}")
            print(f"   Background Highlighting: {ifd_config.get('show_confidence_background', False)}")
            print(f"   Performance Mode: {ifd_config.get('performance', {}).get('max_signals_display', 'N/A')} max signals")

        except Exception as e:
            print(f"❌ Error loading {config_name}: {e}")

def demo_chart_initialization():
    """Demonstrate chart initialization with IFD"""
    print("\n=== IFD Chart Initialization Demo ===")

    try:
        config_manager = ChartConfigManager()
        ifd_config = config_manager.load_config("ifd_enabled")

        print("📊 Initializing chart with IFD configuration...")
        chart = NQFiveMinuteChart(config=ifd_config)

        print("✅ Chart initialized successfully!")
        print(f"   IFD Enabled: {'ifd_v3' in chart.indicators_enabled}")
        print(f"   Data Provider IFD: {chart.data_provider.enable_ifd_signals}")

        # Show IFD bridge status
        bridge_status = chart.data_provider.get_ifd_bridge_status()
        print(f"\n🌉 IFD Bridge Status:")
        print(f"   Enabled: {bridge_status.get('enabled', False)}")
        print(f"   Available: {bridge_status.get('available', False)}")
        print(f"   Healthy: {bridge_status.get('healthy', 'Unknown')}")

        return chart

    except Exception as e:
        print(f"❌ Chart initialization failed: {e}")
        return None

def demo_usage_instructions():
    """Show how to use IFD charts in production"""
    print("\n=== Production Usage Instructions ===")

    print("""
🚀 To use IFD charts during market hours:

1️⃣ Basic IFD Chart:
   python scripts/nq_5m_chart.py --config ifd_enabled

2️⃣ Advanced IFD with more indicators:
   python scripts/nq_5m_chart.py --config ifd_advanced

3️⃣ Minimal IFD for performance:
   python scripts/nq_5m_chart.py --config ifd_minimal

4️⃣ Custom settings:
   python scripts/nq_5m_chart.py --config ifd_enabled --hours 6 --update 15

📈 What you'll see:
   • Real-time 5-minute candlestick charts
   • IFD signal overlays (triangles above/below candles)
   • Color-coded by action: Green=BUY, Orange=MONITOR
   • Size-coded by strength: Larger=EXTREME, Smaller=MODERATE
   • Hover tooltips with confidence, action, and timing details

⏰ Best times to test:
   • Monday-Friday 9:30 AM - 4:00 PM ET (Regular trading hours)
   • Sunday-Friday 6:00 PM - 5:00 PM ET (Futures trading hours)
   • Avoid weekends when markets are closed
""")

def main():
    """Run IFD chart demo"""
    print("🎯 IFD v3.0 Chart Integration Demo")
    print("=" * 50)

    # Demo configuration system
    demo_ifd_configuration()

    # Demo chart initialization
    chart = demo_chart_initialization()

    # Show usage instructions
    demo_usage_instructions()

    if chart:
        print("\n✅ IFD Chart Integration is ready for production!")
        print("🎉 All systems operational - try running during market hours")
    else:
        print("\n⚠️ Chart initialization failed - check dependencies")

if __name__ == "__main__":
    main()
