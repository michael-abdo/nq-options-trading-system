#!/usr/bin/env python3
"""
Auto Screenshot Tool - Takes screenshot of entire screen
"""

import subprocess
import time
from datetime import datetime
from pathlib import Path

def take_auto_screenshot():
    """Take automatic screenshot of entire screen"""

    # Create screenshots directory
    screenshot_dir = Path("/Users/Mike/trading/algos/EOD/tests/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = screenshot_dir / f"dashboard_{timestamp}.png"
    latest_filename = screenshot_dir / "dashboard_latest.png"

    print("📷 Taking automatic screenshot in 3 seconds...")
    print("🖥️  Make sure the dashboard is visible on screen!")

    # Countdown
    for i in range(3, 0, -1):
        print(f"   {i}...")
        time.sleep(1)

    try:
        # Take full screen screenshot (no interaction needed)
        print("📸 Capturing screen...")
        subprocess.run(["screencapture", str(filename)], check=True)

        # Copy to latest
        subprocess.run(["cp", str(filename), str(latest_filename)], check=True)

        print(f"✅ Screenshot saved: {filename}")
        print(f"✅ Latest screenshot: {latest_filename}")

        # Show file info
        if latest_filename.exists():
            size_kb = latest_filename.stat().st_size / 1024
            print(f"📊 File size: {size_kb:.1f} KB")

        return str(latest_filename)

    except Exception as e:
        print(f"❌ Screenshot failed: {e}")
        print("💡 Try: screencapture ~/Desktop/dashboard.png")
        return None

if __name__ == "__main__":
    take_auto_screenshot()
