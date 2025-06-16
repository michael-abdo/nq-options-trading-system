#!/usr/bin/env python3
"""
Test Phase 2 WebSocket Integration

Tests the complete integration between:
1. StreamingBridge with WebSocket server
2. WebSocket signal broadcasting
3. Dashboard WebSocket client connectivity
"""

import unittest
import os
import sys
import time
import json
import threading
import asyncio
import websocket

# Add project paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestPhase2WebSocketIntegration(unittest.TestCase):
    """Test Phase 2 WebSocket integration components"""

    def setUp(self):
        """Set up test fixtures"""
        self.websocket_server = None
        self.streaming_bridge = None
        self.test_signals_received = []
        self.connection_established = False

    def tearDown(self):
        """Clean up after tests"""
        if self.streaming_bridge:
            self.streaming_bridge.stop()
        if self.websocket_server:
            self.websocket_server.stop_server()

    def test_websocket_server_creation(self):
        """Test WebSocket server can be created and started"""
        print("\n🧪 Testing WebSocket Server Creation")

        try:
            from tasks.options_trading_system.analysis_engine.live_streaming.websocket_server import create_dashboard_websocket_server

            # Create server
            server = create_dashboard_websocket_server(host='localhost', port=8766)
            self.assertIsNotNone(server)
            self.assertEqual(server.host, 'localhost')
            self.assertEqual(server.port, 8766)

            # Start server
            server.start_server()
            time.sleep(1)  # Wait for startup

            self.assertTrue(server.is_running)
            print("   ✅ WebSocket server created and started successfully")

            # Stop server
            server.stop_server()
            time.sleep(1)

            self.assertFalse(server.is_running)
            print("   ✅ WebSocket server stopped successfully")

        except Exception as e:
            self.fail(f"WebSocket server creation failed: {e}")

    def test_streaming_bridge_websocket_integration(self):
        """Test StreamingBridge integrates with WebSocket server"""
        print("\n🧪 Testing StreamingBridge WebSocket Integration")

        try:
            from tasks.options_trading_system.analysis_engine.live_streaming import create_streaming_bridge

            # Configuration with WebSocket enabled
            config = {
                'mode': 'development',
                'data_simulation': True,
                'market_hours_enforcement': False,
                'enable_websocket_server': True,
                'websocket_host': 'localhost',
                'websocket_port': 8767
            }

            # Create streaming bridge
            bridge = create_streaming_bridge(config)
            self.assertIsNotNone(bridge)

            # Initialize components (includes WebSocket server)
            success = bridge.initialize_components()
            self.assertTrue(success)

            # Verify WebSocket server was created
            self.assertIsNotNone(bridge.websocket_server)
            self.assertTrue(bridge.websocket_server.is_running)
            print("   ✅ StreamingBridge created WebSocket server successfully")

            # Verify WebSocket broadcaster was created
            self.assertIsNotNone(bridge.websocket_broadcaster)
            print("   ✅ WebSocket broadcaster initialized successfully")

            # Test bridge status includes WebSocket info
            status = bridge.get_bridge_status()
            self.assertIn('websocket_server', status)
            websocket_status = status['websocket_server']
            self.assertTrue(websocket_status['enabled'])
            self.assertTrue(websocket_status['running'])
            self.assertEqual(websocket_status['host'], 'localhost')
            self.assertEqual(websocket_status['port'], 8767)
            print("   ✅ Bridge status includes WebSocket server information")

            # Clean up
            bridge.stop()
            time.sleep(1)

        except Exception as e:
            self.fail(f"StreamingBridge WebSocket integration failed: {e}")

    def test_websocket_client_connection(self):
        """Test WebSocket client can connect and receive signals"""
        print("\n🧪 Testing WebSocket Client Connection and Signal Reception")

        try:
            from tasks.options_trading_system.analysis_engine.live_streaming.websocket_server import create_dashboard_websocket_server

            # Start WebSocket server
            server = create_dashboard_websocket_server(host='localhost', port=8768)
            server.start_server()
            time.sleep(1)

            # Test client connection
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    self.test_signals_received.append(data)
                    if data.get('type') == 'connection':
                        self.connection_established = True
                except:
                    pass

            def on_open(ws):
                # Send subscription
                subscribe_msg = {'type': 'subscribe', 'signal_types': ['all']}
                ws.send(json.dumps(subscribe_msg))

            def on_error(ws, error):
                print(f"   WebSocket client error: {error}")

            # Create WebSocket client
            client = websocket.WebSocketApp(
                "ws://localhost:8768",
                on_open=on_open,
                on_message=on_message,
                on_error=on_error
            )

            # Run client in background
            client_thread = threading.Thread(target=client.run_forever, daemon=True)
            client_thread.start()

            # Wait for connection
            time.sleep(2)
            self.assertTrue(self.connection_established, "WebSocket connection not established")
            print("   ✅ WebSocket client connected successfully")

            # Send test signal through server
            test_signal = {
                'strike': 22000,
                'option_type': 'C',
                'signal_strength': 'EXTREME',
                'final_confidence': 0.95,
                'action': 'STRONG_BUY'
            }

            server.send_signal_sync(test_signal)
            time.sleep(1)

            # Check if signal was received
            signal_received = any(
                msg.get('type') == 'ifd_signal'
                for msg in self.test_signals_received
            )
            self.assertTrue(signal_received, "Test signal not received by client")
            print("   ✅ Signal broadcasted and received successfully")

            # Clean up
            client.close()
            server.stop_server()
            time.sleep(1)

        except Exception as e:
            self.fail(f"WebSocket client connection test failed: {e}")

    def test_signal_formatting_for_dashboard(self):
        """Test signal formatting for dashboard consumption"""
        print("\n🧪 Testing Signal Formatting for Dashboard")

        try:
            from tasks.options_trading_system.analysis_engine.live_streaming.websocket_server import DashboardWebSocketServer

            server = DashboardWebSocketServer()

            # Test signal formatting
            test_signal = {
                'strike': 22000,
                'option_type': 'C',
                'signal_strength': 'EXTREME',
                'final_confidence': 0.95,
                'action': 'STRONG_BUY',
                'pressure_ratio': 3.2,
                'total_volume': 1500,
                'market_price': 22025.50
            }

            formatted = server.format_signal_for_dashboard(test_signal)

            # Verify formatted signal structure
            self.assertIsNotNone(formatted)
            self.assertEqual(formatted['type'], 'ifd_signal')
            self.assertIn('timestamp', formatted)
            self.assertIn('signal', formatted)
            self.assertIn('metadata', formatted)

            # Verify signal data
            signal_data = formatted['signal']
            self.assertEqual(signal_data['strike'], 22000)
            self.assertEqual(signal_data['option_type'], 'C')
            self.assertEqual(signal_data['signal_strength'], 'EXTREME')
            self.assertEqual(signal_data['final_confidence'], 0.95)
            self.assertEqual(signal_data['action'], 'STRONG_BUY')

            # Verify metadata
            metadata = formatted['metadata']
            self.assertEqual(metadata['source'], 'ifd_v3_live')
            self.assertIn('signal_id', metadata)

            print("   ✅ Signal formatting works correctly")
            print(f"   📄 Formatted signal keys: {list(formatted.keys())}")

        except Exception as e:
            self.fail(f"Signal formatting test failed: {e}")

    def test_connection_status_tracking(self):
        """Test connection status tracking and reporting"""
        print("\n🧪 Testing Connection Status Tracking")

        try:
            from tasks.options_trading_system.analysis_engine.live_streaming.websocket_server import create_dashboard_websocket_server

            server = create_dashboard_websocket_server(host='localhost', port=8769)

            # Initial status
            status = asyncio.run(server.get_server_status())
            self.assertEqual(status['type'], 'server_status')
            self.assertFalse(status['status']['running'])
            self.assertEqual(status['status']['connections_active'], 0)
            print("   ✅ Initial server status reported correctly")

            # Start server and check status
            server.start_server()
            time.sleep(1)

            status = asyncio.run(server.get_server_status())
            self.assertTrue(status['status']['running'])
            self.assertEqual(status['status']['host'], 'localhost')
            self.assertEqual(status['status']['port'], 8769)
            print("   ✅ Running server status reported correctly")

            # Stop server and check status
            server.stop_server()
            time.sleep(1)

            self.assertFalse(server.is_running)
            print("   ✅ Server status tracking works correctly")

        except Exception as e:
            self.fail(f"Connection status tracking test failed: {e}")

def run_phase2_integration_tests():
    """Run all Phase 2 integration tests"""
    print("=" * 70)
    print("PHASE 2 WEBSOCKET INTEGRATION TESTS")
    print("=" * 70)

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase2WebSocketIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print("\nFAILURES:")
        for test, failure in result.failures:
            print(f"  - {test}: {failure}")

    if result.errors:
        print("\nERRORS:")
        for test, error in result.errors:
            print(f"  - {test}: {error}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅ ALL TESTS PASSED' if success else '❌ SOME TESTS FAILED'}")

    return success

if __name__ == "__main__":
    run_phase2_integration_tests()
