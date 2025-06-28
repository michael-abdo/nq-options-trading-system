#!/usr/bin/env python3
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
                print(f"\n📊 Received Tradovate data at {datetime.now()}")
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
    server = HTTPServer(('localhost', 8082), TradovateDataHandler)
    print('🚀 Tradovate Data Receiver running on http://localhost:8082')
    print('📡 Endpoint: POST http://localhost:8082/api/tradovate-data')
    print('⏸️  Press Ctrl+C to stop\n')
    server.serve_forever()
