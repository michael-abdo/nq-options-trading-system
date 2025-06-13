#!/usr/bin/env python3
"""
Quick Chart - Fast 5-minute chart generation
Simple script to quickly generate and save a 5-minute chart
"""

import sys
import os
from pathlib import Path

# Add parent directories to path
script_dir = Path(__file__).parent
sys.path.append(str(script_dir.parent))
sys.path.append(str(script_dir.parent.parent))

from nq_5m_chart import NQFiveMinuteChart
from chart_config_manager import ChartConfigManager
from utils.timezone_utils import format_eastern_timestamp

def main():
    """Generate a quick 5-minute chart"""
    print("🚀 Quick NQ 5-Minute Chart Generator")
    print("=" * 40)

    # Initialize configuration manager
    config_manager = ChartConfigManager()

    # Load minimal config for speed
    config = config_manager.load_config("minimal")

    # Override for quick generation
    config["chart"]["time_range_hours"] = 2
    config["chart"]["show_volume"] = True
    config["indicators"]["enabled"] = ["sma"]

    print(f"📊 Generating chart with 2-hour time range...")
    print(f"⚡ Using minimal configuration for speed")

    try:
        # Create chart
        chart = NQFiveMinuteChart(config=config)

        # Generate filename with timestamp
        timestamp = format_eastern_timestamp()
        filename = f"outputs/quick_chart_{timestamp}.html"

        # Save chart
        result = chart.save_chart(filename)

        if result:
            print(f"✅ Chart saved successfully!")
            print(f"📁 File: {result}")
            print(f"🌐 Open in browser: file://{os.path.abspath(result)}")
        else:
            print("❌ Failed to generate chart")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
