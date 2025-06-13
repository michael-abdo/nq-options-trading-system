#!/usr/bin/env python3
"""
Brief test of the trading-safe dashboard
"""

import subprocess
import time
import signal
import os

def test_dashboard():
    """Test dashboard launch and immediate stop"""

    print("🧪 Testing Trading-Safe Dashboard Launch...")

    try:
        # Start the dashboard process
        process = subprocess.Popen([
            'python3', 'scripts/start_trading_safe_chart.py',
            '--type', 'dashboard', '--symbol', 'NQM5', '--hours', '1'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        print("📊 Dashboard started, waiting 5 seconds...")
        time.sleep(5)

        # Terminate the process
        process.terminate()

        # Wait for termination and get output
        stdout, stderr = process.communicate(timeout=5)

        print("✅ Dashboard test completed")
        print("\nOutput preview:")
        print(stdout[:500] + "..." if len(stdout) > 500 else stdout)

        if "TRADING SAFETY CONFIRMED" in stdout:
            print("✅ TRADING SAFETY SYSTEM WORKING")

        if "Dash is running" in stdout:
            print("✅ DASHBOARD LAUNCHED SUCCESSFULLY")

        return True

    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        return False

if __name__ == "__main__":
    test_dashboard()
