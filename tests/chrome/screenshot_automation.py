#!/usr/bin/env python3
"""
Automated Screenshot Capture for IFD Dashboard
Uses Chrome DevTools Protocol to capture dashboard screenshots
"""

import json
import base64
import requests
import time
from datetime import datetime
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class DashboardScreenshot:
    """Capture screenshots of the IFD dashboard"""

    def __init__(self, debug_port=9222):
        self.debug_port = debug_port
        self.base_url = f"http://localhost:{debug_port}"
        self.screenshots_dir = "outputs/monitoring/screenshots"

        # Create screenshots directory
        os.makedirs(self.screenshots_dir, exist_ok=True)

    def get_tabs(self):
        """Get list of open tabs"""
        try:
            response = requests.get(f"{self.base_url}/json")
            return response.json()
        except Exception as e:
            print(f"Error connecting to Chrome: {e}")
            return []

    def capture_screenshot(self, tab_id=None):
        """Capture screenshot of dashboard"""
        print("\n📸 Capturing Dashboard Screenshot...")

        # Get tabs
        tabs = self.get_tabs()
        if not tabs:
            print("❌ No Chrome tabs found")
            return None

        # Find dashboard tab
        dashboard_tab = None
        dashboard_url = "http://localhost:8080/dashboard.html"

        for tab in tabs:
            if dashboard_url in tab.get('url', '') or (tab_id and tab['id'] == tab_id):
                dashboard_tab = tab
                break

        if not dashboard_tab:
            print(f"❌ Dashboard not found. Opening {dashboard_url}...")
            # Create new tab with dashboard
            response = requests.put(f"{self.base_url}/json/new?{dashboard_url}")
            time.sleep(3)  # Wait for page to load
            tabs = self.get_tabs()
            for tab in tabs:
                if dashboard_url in tab.get('url', ''):
                    dashboard_tab = tab
                    break

        if not dashboard_tab:
            print("❌ Could not open dashboard")
            return None

        print(f"✅ Found dashboard: {dashboard_tab['title']}")

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dashboard_screenshot_{timestamp}.png"
        filepath = os.path.join(self.screenshots_dir, filename)

        print(f"💾 Screenshot will be saved to: {filepath}")

        # Note: Full screenshot capture requires Chrome DevTools Protocol
        # This is a placeholder for the actual implementation
        print("📝 Note: Full screenshot requires websocket connection to Chrome DevTools")
        print("   For now, creating a placeholder...")

        # Create info file about the screenshot
        info_file = filepath.replace('.png', '_info.json')
        screenshot_info = {
            'timestamp': timestamp,
            'url': dashboard_tab.get('url', ''),
            'title': dashboard_tab.get('title', ''),
            'tab_id': dashboard_tab.get('id', ''),
            'status': 'ready_for_capture'
        }

        with open(info_file, 'w') as f:
            json.dump(screenshot_info, f, indent=2)

        print(f"✅ Screenshot info saved: {info_file}")

        return filepath

    def capture_multiple(self, count=5, interval=60):
        """Capture multiple screenshots over time"""
        print(f"\n📸 Starting automated screenshot capture")
        print(f"   Count: {count}")
        print(f"   Interval: {interval} seconds")
        print("   Press Ctrl+C to stop\n")

        screenshots = []

        try:
            for i in range(count):
                print(f"\n[{i+1}/{count}] Capturing screenshot...")
                filepath = self.capture_screenshot()
                if filepath:
                    screenshots.append(filepath)

                if i < count - 1:
                    print(f"⏱️  Waiting {interval} seconds...")
                    time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n⚠️  Screenshot capture interrupted")

        # Summary
        print("\n" + "="*60)
        print("📊 SCREENSHOT CAPTURE SUMMARY")
        print("="*60)
        print(f"Screenshots captured: {len(screenshots)}")
        print(f"Location: {self.screenshots_dir}")

        return screenshots

    def list_screenshots(self):
        """List all captured screenshots"""
        print(f"\n📁 Screenshots in {self.screenshots_dir}:")

        try:
            files = os.listdir(self.screenshots_dir)
            json_files = [f for f in files if f.endswith('_info.json')]

            if not json_files:
                print("   No screenshots found")
                return

            for json_file in sorted(json_files, reverse=True)[:10]:  # Show last 10
                filepath = os.path.join(self.screenshots_dir, json_file)
                with open(filepath, 'r') as f:
                    info = json.load(f)

                print(f"\n   📸 {info['timestamp']}")
                print(f"      URL: {info['url']}")
                print(f"      Title: {info['title']}")
                print(f"      Status: {info['status']}")

        except Exception as e:
            print(f"   Error listing screenshots: {e}")

def main():
    """Run screenshot automation"""
    print("🖼️  IFD Dashboard Screenshot Automation")
    print("="*60)

    # Create screenshot manager
    screenshot = DashboardScreenshot()

    # Check Chrome connection
    tabs = screenshot.get_tabs()
    if not tabs:
        print("\n⚠️  Chrome Remote Debugging not available")
        print("Start Chrome with: --remote-debugging-port=9222")
        return

    print(f"✅ Connected to Chrome (found {len(tabs)} tabs)")

    # Menu
    while True:
        print("\n" + "="*60)
        print("📸 SCREENSHOT OPTIONS")
        print("="*60)
        print("1. Capture single screenshot")
        print("2. Capture multiple screenshots (time-lapse)")
        print("3. List existing screenshots")
        print("4. Exit")

        choice = input("\nSelect option (1-4): ").strip()

        if choice == '1':
            screenshot.capture_screenshot()

        elif choice == '2':
            count = int(input("Number of screenshots (default 5): ") or "5")
            interval = int(input("Interval in seconds (default 60): ") or "60")
            screenshot.capture_multiple(count, interval)

        elif choice == '3':
            screenshot.list_screenshots()

        elif choice == '4':
            print("\n👋 Exiting screenshot automation")
            break

        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main()
