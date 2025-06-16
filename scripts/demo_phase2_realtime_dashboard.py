#!/usr/bin/env python3
"""
Phase 2 Real-time Dashboard Demo

This script demonstrates the complete Phase 2 implementation:
1. Live streaming analysis engine with WebSocket server
2. Real-time dashboard with live signal overlays
3. WebSocket communication between analysis engine and dashboard

Usage:
    python3 demo_phase2_realtime_dashboard.py

This will start:
- Analysis engine with live streaming and WebSocket server (port 8765)
- Enhanced dashboard with real-time signal display (port 8051)
"""

import os
import sys
import time
import threading
import logging
import signal
import subprocess
import webbrowser

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Phase2Demo:
    """Demonstrates complete Phase 2 real-time dashboard implementation"""

    def __init__(self):
        self.analysis_engine_process = None
        self.dashboard_process = None
        self.running = True

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def start_analysis_engine(self):
        """Start the analysis engine with live streaming and WebSocket server"""
        logger.info("🚀 Starting Analysis Engine with Live Streaming...")

        try:
            # Import and start streaming bridge
            from tasks.options_trading_system.analysis_engine.live_streaming import create_streaming_bridge

            # Configuration for demo mode
            config = {
                'mode': 'development',  # Development mode for demo
                'data_simulation': True,  # Use simulated data
                'market_hours_enforcement': False,  # Allow demo outside market hours
                'enable_websocket_server': True,
                'websocket_host': 'localhost',
                'websocket_port': 8765,
                'simulation_interval': 3  # Send signals every 3 seconds
            }

            # Create and start streaming bridge
            self.streaming_bridge = create_streaming_bridge(config)

            # Start streaming in background thread
            def run_streaming():
                logger.info("📡 Starting live streaming simulation...")
                self.streaming_bridge.start_streaming()

                # Keep running until stopped
                while self.running:
                    time.sleep(1)

            self.streaming_thread = threading.Thread(target=run_streaming, daemon=True)
            self.streaming_thread.start()

            logger.info("✅ Analysis Engine started with WebSocket server on port 8765")

        except Exception as e:
            logger.error(f"❌ Failed to start analysis engine: {e}")
            raise

    def start_dashboard(self):
        """Start the enhanced real-time dashboard"""
        logger.info("📊 Starting Enhanced Real-time Dashboard...")

        try:
            # Import and start dashboard
            from scripts.nq_realtime_ifd_dashboard import NQRealtimeIFDDashboard

            # Create dashboard with demo configuration
            self.dashboard = NQRealtimeIFDDashboard(
                symbol="NQM5",
                hours=4,
                update_interval=5,  # Update every 5 seconds
                port=8051,
                websocket_uri="ws://localhost:8765"
            )

            # Start dashboard in background thread
            def run_dashboard():
                logger.info("🌐 Starting dashboard server...")
                self.dashboard.run(debug=False, open_browser=False)

            self.dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
            self.dashboard_thread.start()

            logger.info("✅ Enhanced Dashboard started on port 8051")

        except Exception as e:
            logger.error(f"❌ Failed to start dashboard: {e}")
            raise

    def open_browser_to_dashboard(self):
        """Open browser to dashboard after startup delay"""
        def delayed_browser_open():
            time.sleep(5)  # Wait for servers to fully start
            logger.info("🌍 Opening browser to dashboard...")
            webbrowser.open('http://127.0.0.1:8051')

        browser_thread = threading.Thread(target=delayed_browser_open, daemon=True)
        browser_thread.start()

    def run_demo(self):
        """Run the complete Phase 2 demo"""
        logger.info("=" * 70)
        logger.info("PHASE 2 REAL-TIME DASHBOARD DEMO")
        logger.info("=" * 70)
        logger.info("Starting comprehensive real-time dashboard demonstration...")

        try:
            # 1. Start Analysis Engine with WebSocket Server
            self.start_analysis_engine()
            time.sleep(2)

            # 2. Start Enhanced Dashboard
            self.start_dashboard()
            time.sleep(2)

            # 3. Open browser to dashboard
            self.open_browser_to_dashboard()

            # 4. Display demo information
            self.display_demo_info()

            # 5. Keep demo running
            logger.info("✅ Phase 2 Demo running successfully!")
            logger.info("Press Ctrl+C to stop the demo")

            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("🛑 Demo stop requested by user")
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
        finally:
            self.cleanup()

    def display_demo_info(self):
        """Display demo information"""
        logger.info("\n" + "=" * 50)
        logger.info("📋 PHASE 2 DEMO INFORMATION")
        logger.info("=" * 50)
        logger.info("🔹 Analysis Engine: http://localhost:8765 (WebSocket)")
        logger.info("🔹 Enhanced Dashboard: http://localhost:8051")
        logger.info("🔹 Mode: Development with simulated signals")
        logger.info("🔹 Signal Generation: Every 3 seconds")
        logger.info("🔹 Dashboard Updates: Every 5 seconds")
        logger.info("")
        logger.info("📊 FEATURES DEMONSTRATED:")
        logger.info("   ✅ Real-time WebSocket communication")
        logger.info("   ✅ Live signal overlays with confidence levels")
        logger.info("   ✅ Connection status indicators")
        logger.info("   ✅ Signal strength visualization (EXTREME/HIGH/MODERATE)")
        logger.info("   ✅ Live timestamp display")
        logger.info("   ✅ Signal confidence meters")
        logger.info("   ✅ User controls for signal sensitivity")
        logger.info("   ✅ Graceful fallback to historical data")
        logger.info("   ✅ Clear distinction between live/historical signals")
        logger.info("")
        logger.info("🎯 EXPECTED BEHAVIOR:")
        logger.info("   • Dashboard should show 🟢 CONNECTED status")
        logger.info("   • Live signals appear as colored triangles on chart")
        logger.info("   • Signal cards appear in bottom panel")
        logger.info("   • Signal count increases over time")
        logger.info("   • Last signal time updates regularly")
        logger.info("=" * 50)

    def cleanup(self):
        """Clean up resources"""
        logger.info("🧹 Cleaning up demo resources...")

        self.running = False

        # Stop streaming bridge
        if hasattr(self, 'streaming_bridge'):
            try:
                self.streaming_bridge.stop()
                logger.info("✅ Analysis engine stopped")
            except Exception as e:
                logger.error(f"Error stopping analysis engine: {e}")

        # Stop dashboard
        if hasattr(self, 'dashboard'):
            try:
                self.dashboard.websocket_client.disconnect()
                logger.info("✅ Dashboard WebSocket disconnected")
            except Exception as e:
                logger.error(f"Error stopping dashboard: {e}")

        logger.info("🏁 Phase 2 Demo cleanup completed")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("🛑 Shutdown signal received")
        self.running = False

def main():
    """Main function"""
    print("Starting Phase 2 Real-time Dashboard Demo...")

    # Check if required dependencies are available
    try:
        import websockets
        import dash
        import plotly
    except ImportError as e:
        print(f"❌ Missing required dependency: {e}")
        print("Please install required packages:")
        print("pip install websockets dash plotly")
        return

    # Run demo
    demo = Phase2Demo()
    demo.run_demo()

if __name__ == "__main__":
    main()
