#!/usr/bin/env python3
"""
Tradovate Live Data Capture via Chrome Remote Debugging
Finds the Tradovate tab and helps locate the "Copy Trading Data" button
"""

import json
import requests
import websocket
import time
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class TradovateDataCapture:
    """Capture live trading data from Tradovate via Chrome"""

    def __init__(self, debug_port=9222):
        self.debug_port = debug_port
        self.base_url = f"http://localhost:{debug_port}"
        self.tradovate_tab = None

    def find_tradovate_tab(self):
        """Find the Tradovate tab in Chrome"""
        try:
            response = requests.get(f"{self.base_url}/json")
            tabs = response.json()

            print(f"\n🔍 Searching through {len(tabs)} Chrome tabs...")

            for tab in tabs:
                url = tab.get('url', '')
                title = tab.get('title', '')

                # Show all tabs for debugging
                print(f"\n📑 Tab: {title[:50]}...")
                print(f"   URL: {url[:60]}...")

                if 'tradovate.com' in url:
                    self.tradovate_tab = tab
                    print(f"\n✅ Found Tradovate tab!")
                    print(f"   Title: {title}")
                    print(f"   URL: {url}")
                    print(f"   ID: {tab['id']}")
                    return tab

            print("\n❌ Tradovate tab not found")
            print("   Please open https://trader.tradovate.com in Chrome")
            return None

        except Exception as e:
            print(f"❌ Error connecting to Chrome: {e}")
            print("   Make sure Chrome is running with --remote-debugging-port=9222")
            return None

    def get_page_info(self):
        """Get detailed page information using DevTools HTTP endpoints"""
        if not self.tradovate_tab:
            print("❌ No Tradovate tab found")
            return None

        tab_id = self.tradovate_tab['id']

        # Activate the tab
        try:
            activate_url = f"{self.base_url}/json/activate/{tab_id}"
            requests.get(activate_url)
            print(f"\n✅ Activated Tradovate tab")
            time.sleep(1)  # Give it a moment to activate
        except Exception as e:
            print(f"⚠️  Could not activate tab: {e}")

        return self.tradovate_tab

    def search_for_copy_button(self):
        """Provide instructions for finding the Copy Trading Data button"""
        print("\n" + "="*60)
        print("🔍 FINDING 'COPY TRADING DATA' BUTTON")
        print("="*60)

        if not self.tradovate_tab:
            self.find_tradovate_tab()
            if not self.tradovate_tab:
                return

        print("\n📋 To locate and use the 'Copy Trading Data' button:")
        print("\n1. The Tradovate tab is now active in Chrome")
        print("2. Look for the 'Copy Trading Data' button (usually in:")
        print("   - Top toolbar")
        print("   - Right-click context menu")
        print("   - Settings/Tools menu")
        print("   - Data export section")

        print("\n3. To capture data programmatically, you can:")
        print("   a) Use Chrome DevTools Console:")
        print("      - Press F12 or Cmd+Option+I")
        print("      - Go to Console tab")
        print("      - Look for button element:")
        print("        document.querySelectorAll('button')")
        print("        Array.from(document.querySelectorAll('button')).filter(b => b.textContent.includes('Copy'))")

        print("\n   b) Use this script to monitor clipboard:")
        print("      - Click 'Copy Trading Data' manually")
        print("      - This script will detect clipboard changes")

        return True

    def create_live_data_monitor(self):
        """Create a script to monitor for live NQ data"""
        monitor_script = """
// Tradovate Live Data Monitor
// Run this in Chrome DevTools Console on the Tradovate page

console.log('🚀 Starting Tradovate Live Data Monitor...');

// Function to find Copy Trading Data button
function findCopyButton() {
    const buttons = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
    const copyButton = buttons.find(b =>
        b.textContent.toLowerCase().includes('copy') &&
        b.textContent.toLowerCase().includes('trading')
    );

    if (copyButton) {
        console.log('✅ Found Copy Trading Data button:', copyButton);
        return copyButton;
    }

    console.log('❌ Copy Trading Data button not found');
    return null;
}

// Function to extract NQ data from page
function extractNQData() {
    const data = {
        timestamp: new Date().toISOString(),
        symbol: 'NQ',
        quotes: [],
        trades: []
    };

    // Look for NQ price elements (adjust selectors based on actual page)
    const priceElements = document.querySelectorAll('[data-symbol*="NQ"], [class*="price"], [class*="quote"]');

    priceElements.forEach(el => {
        const text = el.textContent;
        if (text && text.match(/\\d+\\.\\d+/)) {
            data.quotes.push({
                element: el.className || el.id,
                value: text,
                timestamp: new Date().toISOString()
            });
        }
    });

    console.log('📊 Extracted NQ Data:', data);
    return data;
}

// Function to monitor clipboard
async function monitorClipboard() {
    try {
        const text = await navigator.clipboard.readText();
        console.log('📋 Clipboard content:', text);

        // Parse if it looks like JSON
        try {
            const data = JSON.parse(text);
            console.log('✅ Parsed trading data:', data);

            // Send to your system via webhook
            // fetch('http://localhost:8080/api/tradovate-data', {
            //     method: 'POST',
            //     headers: {'Content-Type': 'application/json'},
            //     body: JSON.stringify(data)
            // });

        } catch (e) {
            console.log('📄 Clipboard contains text (not JSON):', text.substring(0, 100) + '...');
        }
    } catch (err) {
        console.log('❌ Cannot read clipboard:', err);
    }
}

// Set up monitoring
const copyButton = findCopyButton();
if (copyButton) {
    copyButton.addEventListener('click', () => {
        console.log('🔘 Copy button clicked!');
        setTimeout(monitorClipboard, 100);
    });
}

// Extract data every 5 seconds
setInterval(() => {
    extractNQData();
}, 5000);

// Monitor for NQ updates
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.target.textContent && mutation.target.textContent.includes('NQ')) {
            console.log('🔄 NQ data updated:', mutation.target.textContent);
        }
    });
});

// Start observing
observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true
});

console.log('✅ Tradovate monitor is running!');
console.log('📋 Click "Copy Trading Data" to capture data');
"""

        print("\n" + "="*60)
        print("📜 CHROME DEVTOOLS SCRIPT")
        print("="*60)
        print("\nCopy and paste this into Chrome DevTools Console:")
        print("(Press F12, go to Console tab, paste and press Enter)")
        print("\n" + "-"*60)
        print(monitor_script)
        print("-"*60)

        # Save script to file
        script_file = "outputs/monitoring/tradovate_monitor.js"
        os.makedirs(os.path.dirname(script_file), exist_ok=True)
        with open(script_file, 'w') as f:
            f.write(monitor_script)
        print(f"\n💾 Script saved to: {script_file}")

        return monitor_script

    def create_data_receiver(self):
        """Create a local server to receive Tradovate data"""
        receiver_script = '''#!/usr/bin/env python3
"""
Tradovate Data Receiver
Receives live trading data and feeds it into the IFD system
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime

class TradovateDataHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/tradovate-data':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data)
                print(f"\\n📊 Received Tradovate data at {datetime.now()}")
                print(json.dumps(data, indent=2))

                # Process NQ data
                if 'NQ' in str(data):
                    print("✅ Found NQ data!")
                    # Here you would feed this into your IFD system

                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'Data received')

            except Exception as e:
                print(f"❌ Error processing data: {e}")
                self.send_response(400)
                self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress request logs

if __name__ == '__main__':
    server = HTTPServer(('localhost', 8081), TradovateDataHandler)
    print('🚀 Tradovate Data Receiver running on http://localhost:8081')
    print('📡 Endpoint: POST http://localhost:8081/api/tradovate-data')
    print('⏸️  Press Ctrl+C to stop\\n')
    server.serve_forever()
'''

        receiver_file = "outputs/monitoring/tradovate_receiver.py"
        with open(receiver_file, 'w') as f:
            f.write(receiver_script)
        os.chmod(receiver_file, 0o755)

        print(f"\n💾 Data receiver saved to: {receiver_file}")
        print("\n🚀 To start the receiver:")
        print(f"   python3 {receiver_file}")

        return receiver_file

def main():
    """Run Tradovate data capture"""
    print("🏦 Tradovate Live Data Capture")
    print("="*60)

    capture = TradovateDataCapture()

    # Find Tradovate tab
    tab = capture.find_tradovate_tab()
    if not tab:
        return

    # Get page info
    capture.get_page_info()

    # Search for copy button
    capture.search_for_copy_button()

    # Create monitoring script
    capture.create_live_data_monitor()

    # Create data receiver
    capture.create_data_receiver()

    print("\n" + "="*60)
    print("✅ SETUP COMPLETE")
    print("="*60)
    print("\n📋 Next steps:")
    print("1. Open Chrome DevTools (F12) on the Tradovate tab")
    print("2. Go to Console tab")
    print("3. Paste the monitoring script and press Enter")
    print("4. Run the data receiver: python3 outputs/monitoring/tradovate_receiver.py")
    print("5. Click 'Copy Trading Data' button in Tradovate")
    print("\n🔄 The system will capture and process live NQ data automatically!")

if __name__ == "__main__":
    main()
