#!/usr/bin/env python3
"""
Dashboard Screenshot Tool
Takes a screenshot of the running dashboard for debugging
"""

import os
import time
import subprocess
from datetime import datetime
from pathlib import Path

def take_screenshot():
    """Take a screenshot of the dashboard using screencapture (macOS)"""

    # Create screenshots directory
    screenshot_dir = Path("/Users/Mike/trading/algos/EOD/tests/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = screenshot_dir / f"dashboard_{timestamp}.png"
    latest_filename = screenshot_dir / "dashboard_latest.png"

    print("📷 Taking dashboard screenshot...")
    print("⏳ Please make sure the dashboard is visible on screen")
    print("   (You have 3 seconds to switch to the dashboard window)")

    # Give user time to switch to dashboard
    for i in range(3, 0, -1):
        print(f"   {i}...")
        time.sleep(1)

    # Take screenshot using macOS screencapture
    try:
        # Interactive mode - click and drag to select area
        print("📸 Click and drag to select the dashboard area...")
        subprocess.run(["screencapture", "-i", str(filename)], check=True)

        # Copy to latest
        if filename.exists():
            subprocess.run(["cp", str(filename), str(latest_filename)], check=True)
            print(f"✅ Screenshot saved: {filename}")
            print(f"✅ Latest screenshot: {latest_filename}")
            return str(latest_filename)
        else:
            print("❌ No screenshot was taken")
            return None

    except subprocess.CalledProcessError as e:
        print(f"❌ Screenshot failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def main():
    """Main function"""
    screenshot_path = take_screenshot()

    if screenshot_path:
        print("\n📊 Screenshot captured successfully!")
        print(f"   View it at: {screenshot_path}")
        print("\n💡 Tip: Use Cmd+Shift+4 for quick screenshots")
        print("   or run this script again for guided capture")

if __name__ == "__main__":
    main()
