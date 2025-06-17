#!/usr/bin/env python3
"""
Live Data Verification System
Compares system data against Tradovate reference to ensure we have REAL live data
"""

import json
import time
import requests
from datetime import datetime, timedelta
import sys
import os
import threading
from collections import deque

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class LiveDataVerifier:
    """Verify system data is truly live by comparing with Tradovate reference"""

    def __init__(self):
        self.tradovate_data = deque(maxlen=100)  # Keep last 100 data points
        self.system_data = deque(maxlen=100)
        self.verification_results = []
        self.is_live = False
        self.last_tradovate_update = None
        self.last_system_update = None

    def receive_tradovate_data(self, data):
        """Receive reference data from Tradovate"""
        timestamp = datetime.now()
        self.last_tradovate_update = timestamp

        # Extract NQ price from Tradovate data
        nq_price = None
        if isinstance(data, dict):
            # Look for NQ price in various possible locations
            if 'price' in data:
                nq_price = data['price']
            elif 'last' in data:
                nq_price = data['last']
            elif 'quotes' in data and data['quotes']:
                nq_price = data['quotes'][0].get('price')

        if nq_price:
            self.tradovate_data.append({
                'timestamp': timestamp,
                'price': float(nq_price),
                'source': 'tradovate'
            })
            print(f"✅ Tradovate Reference: ${nq_price:,.2f} at {timestamp.strftime('%H:%M:%S.%f')[:-3]}")
            self.verify_data_freshness()

    def receive_system_data(self, price, source='databento'):
        """Receive data from our system to verify"""
        timestamp = datetime.now()
        self.last_system_update = timestamp

        self.system_data.append({
            'timestamp': timestamp,
            'price': float(price),
            'source': source
        })

        print(f"📊 System Data ({source}): ${price:,.2f} at {timestamp.strftime('%H:%M:%S.%f')[:-3]}")
        self.verify_data_freshness()

    def verify_data_freshness(self):
        """Compare system data with Tradovate reference"""
        if not self.tradovate_data or not self.system_data:
            return

        # Get latest from each source
        latest_tradovate = self.tradovate_data[-1]
        latest_system = self.system_data[-1]

        # Calculate time difference
        time_diff = abs((latest_system['timestamp'] - latest_tradovate['timestamp']).total_seconds())

        # Calculate price difference
        price_diff = abs(latest_system['price'] - latest_tradovate['price'])
        price_diff_pct = (price_diff / latest_tradovate['price']) * 100

        # Verification criteria
        is_time_fresh = time_diff < 5.0  # Within 5 seconds
        is_price_close = price_diff < 10.0  # Within $10 (0.05% for NQ ~20,000)

        # Overall verification
        is_verified_live = is_time_fresh and is_price_close
        self.is_live = is_verified_live

        # Record result
        result = {
            'timestamp': datetime.now(),
            'time_diff': time_diff,
            'price_diff': price_diff,
            'price_diff_pct': price_diff_pct,
            'is_time_fresh': is_time_fresh,
            'is_price_close': is_price_close,
            'is_live': is_verified_live,
            'tradovate_price': latest_tradovate['price'],
            'system_price': latest_system['price']
        }

        self.verification_results.append(result)

        # Display result
        if is_verified_live:
            print(f"✅ VERIFIED LIVE DATA! Time diff: {time_diff:.1f}s, Price diff: ${price_diff:.2f}")
        else:
            print(f"❌ NOT LIVE! Time diff: {time_diff:.1f}s, Price diff: ${price_diff:.2f}")
            if not is_time_fresh:
                print(f"   ⚠️  Data is {time_diff:.1f} seconds old (max allowed: 5.0s)")
            if not is_price_close:
                print(f"   ⚠️  Price difference too large: ${price_diff:.2f} ({price_diff_pct:.2f}%)")

    def get_verification_status(self):
        """Get current verification status"""
        if not self.verification_results:
            return {
                'status': 'NO_DATA',
                'is_live': False,
                'message': 'Waiting for data from both sources'
            }

        latest = self.verification_results[-1]

        status = {
            'status': 'LIVE' if latest['is_live'] else 'NOT_LIVE',
            'is_live': latest['is_live'],
            'time_diff': latest['time_diff'],
            'price_diff': latest['price_diff'],
            'tradovate_price': latest['tradovate_price'],
            'system_price': latest['system_price'],
            'last_check': latest['timestamp'].isoformat(),
            'message': self._get_status_message(latest)
        }

        return status

    def _get_status_message(self, result):
        """Generate human-readable status message"""
        if result['is_live']:
            return f"Live data verified! Prices match within ${result['price_diff']:.2f}"
        else:
            msgs = []
            if not result['is_time_fresh']:
                msgs.append(f"Data delayed by {result['time_diff']:.1f}s")
            if not result['is_price_close']:
                msgs.append(f"Price mismatch of ${result['price_diff']:.2f}")
            return "Not live: " + ", ".join(msgs)

    def start_verification_server(self, port=8083):
        """Start HTTP server to receive Tradovate data and provide status"""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        verifier = self

        class VerificationHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == '/api/tradovate-data':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)

                    try:
                        data = json.loads(post_data)
                        verifier.receive_tradovate_data(data)

                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()

                        response = {
                            'status': 'received',
                            'verification': verifier.get_verification_status()
                        }
                        self.wfile.write(json.dumps(response).encode())

                    except Exception as e:
                        print(f"❌ Error processing data: {e}")
                        self.send_response(400)
                        self.end_headers()

                elif self.path == '/api/system-data':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)

                    try:
                        data = json.loads(post_data)
                        price = data.get('price')
                        source = data.get('source', 'system')

                        if price:
                            verifier.receive_system_data(price, source)

                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()

                        response = {
                            'status': 'received',
                            'verification': verifier.get_verification_status()
                        }
                        self.wfile.write(json.dumps(response).encode())

                    except Exception as e:
                        print(f"❌ Error processing system data: {e}")
                        self.send_response(400)
                        self.end_headers()
                        data = json.loads(post_data)
                        verifier.receive_tradovate_data(data)

                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()

                        response = {
                            'status': 'received',
                            'verification': verifier.get_verification_status()
                        }
                        self.wfile.write(json.dumps(response).encode())

                    except Exception as e:
                        print(f"❌ Error processing data: {e}")
                        self.send_response(400)
                        self.end_headers()

            def do_GET(self):
                if self.path == '/api/status':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()

                    status = verifier.get_verification_status()
                    self.wfile.write(json.dumps(status, indent=2).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()

            def log_message(self, format, *args):
                pass  # Suppress logs

        server = HTTPServer(('localhost', port), VerificationHandler)
        print(f'🔍 Live Data Verifier running on http://localhost:{port}')
        print(f'📡 Endpoints:')
        print(f'   POST http://localhost:{port}/api/tradovate-data - Receive Tradovate data')
        print(f'   GET  http://localhost:{port}/api/status - Check verification status')
        server.serve_forever()


def create_verification_dashboard():
    """Create a simple HTML dashboard for verification status"""
    dashboard_html = '''<!DOCTYPE html>
<html>
<head>
    <title>Live Data Verification</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; }
        .status-card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .live { border-left: 5px solid #27ae60; }
        .not-live { border-left: 5px solid #e74c3c; }
        .no-data { border-left: 5px solid #95a5a6; }
        h1 { color: #2c3e50; }
        .metric { display: inline-block; margin-right: 30px; }
        .metric-value { font-size: 1.5em; font-weight: bold; }
        .timestamp { color: #666; font-size: 0.9em; }
        #status { font-size: 1.2em; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Live Data Verification Dashboard</h1>

        <div id="statusCard" class="status-card no-data">
            <h2 id="statusTitle">Waiting for Data...</h2>
            <div id="status"></div>
            <div id="metrics"></div>
            <div id="timestamp" class="timestamp"></div>
        </div>

        <div class="status-card">
            <h3>How to Use:</h3>
            <ol>
                <li>Open Tradovate in Chrome</li>
                <li>Run the monitoring script in DevTools</li>
                <li>Click "Copy Trading Data" to send reference data</li>
                <li>Your system data will be compared automatically</li>
            </ol>
        </div>
    </div>

    <script>
        async function updateStatus() {
            try {
                const response = await fetch('http://localhost:8083/api/status');
                const data = await response.json();

                const card = document.getElementById('statusCard');
                const title = document.getElementById('statusTitle');
                const status = document.getElementById('status');
                const metrics = document.getElementById('metrics');
                const timestamp = document.getElementById('timestamp');

                // Update card style
                card.className = 'status-card ' + data.status.toLowerCase().replace('_', '-');

                // Update title
                if (data.status === 'LIVE') {
                    title.textContent = '✅ LIVE DATA VERIFIED';
                } else if (data.status === 'NOT_LIVE') {
                    title.textContent = '❌ NOT LIVE DATA';
                } else {
                    title.textContent = '⏳ Waiting for Data...';
                }

                // Update status message
                status.textContent = data.message;

                // Update metrics
                if (data.tradovate_price) {
                    metrics.innerHTML = `
                        <div class="metric">
                            <div>Tradovate (Reference)</div>
                            <div class="metric-value">$${data.tradovate_price.toFixed(2)}</div>
                        </div>
                        <div class="metric">
                            <div>System Data</div>
                            <div class="metric-value">$${data.system_price.toFixed(2)}</div>
                        </div>
                        <div class="metric">
                            <div>Time Diff</div>
                            <div class="metric-value">${data.time_diff.toFixed(1)}s</div>
                        </div>
                        <div class="metric">
                            <div>Price Diff</div>
                            <div class="metric-value">$${data.price_diff.toFixed(2)}</div>
                        </div>
                    `;
                }

                // Update timestamp
                if (data.last_check) {
                    timestamp.textContent = 'Last check: ' + new Date(data.last_check).toLocaleTimeString();
                }

            } catch (e) {
                console.error('Error updating status:', e);
            }
        }

        // Update every second
        setInterval(updateStatus, 1000);
        updateStatus();
    </script>
</body>
</html>'''

    # Save dashboard
    dashboard_file = 'outputs/monitoring/live_verification.html'
    with open(dashboard_file, 'w') as f:
        f.write(dashboard_html)

    print(f"📊 Verification dashboard saved to: {dashboard_file}")
    return dashboard_file


def main():
    """Run live data verification system"""
    print("🔍 Live Data Verification System")
    print("="*60)
    print("This system ensures you're getting REAL live data, not delayed data")
    print("="*60)

    # Create verifier
    verifier = LiveDataVerifier()

    # Create dashboard
    dashboard_file = create_verification_dashboard()

    # Start verification server
    import threading
    server_thread = threading.Thread(target=verifier.start_verification_server, args=(8083,))
    server_thread.daemon = True
    server_thread.start()

    time.sleep(1)

    print("\n✅ Verification system is running!")
    print("\n📋 Next steps:")
    print("1. Open verification dashboard: http://localhost:8080/live_verification.html")
    print("2. Update Tradovate monitor script to use port 8083")
    print("3. Click 'Copy Trading Data' in Tradovate")
    print("4. Feed your system data to the verifier")

    print("\n📊 To send system data for verification:")
    print("   verifier.receive_system_data(price=21930.50, source='databento')")

    # Example: Simulate system data (replace with real data feed)
    print("\n⏳ Waiting for data... Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
            # In production, you would feed real system data here
            # Example: verifier.receive_system_data(get_current_nq_price())

    except KeyboardInterrupt:
        print("\n\n👋 Verification system stopped")


if __name__ == "__main__":
    main()
