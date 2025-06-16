#!/usr/bin/env python3
"""
Unit tests for Streaming Bridge component
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
from datetime import datetime, timezone

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from ..streaming_bridge import StreamingBridge, create_streaming_bridge


class TestStreamingBridge(unittest.TestCase):
    """Test the StreamingBridge component"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'symbols': ['NQ.OPT'],
            'daily_budget': 25.0,
            'market_hours_enforcement': True,
            'cost_monitoring': True,
            'mode': 'development'
        }

    def tearDown(self):
        """Clean up after tests"""
        pass

    def test_bridge_initialization(self):
        """Test bridge initialization with configuration"""
        bridge = StreamingBridge(self.config)

        self.assertEqual(bridge.config['symbols'], ['NQ.OPT'])
        self.assertEqual(bridge.config['daily_budget'], 25.0)
        self.assertFalse(bridge.is_running)
        self.assertTrue(bridge.components_initialized)

    def test_market_hours_check(self):
        """Test market hours validation"""
        bridge = StreamingBridge(self.config)

        # Mock datetime to be during market hours (Tuesday 2 PM ET)
        with patch('streaming_bridge.get_eastern_time') as mock_time:
            mock_time.return_value = datetime(2025, 6, 17, 14, 0, 0)  # Tuesday 2 PM ET
            self.assertTrue(bridge._check_market_hours())

        # Mock datetime to be outside market hours (Saturday)
        with patch('streaming_bridge.get_eastern_time') as mock_time:
            mock_time.return_value = datetime(2025, 6, 14, 14, 0, 0)  # Saturday
            self.assertFalse(bridge._check_market_hours())

    def test_pressure_metrics_callback(self):
        """Test pressure metrics processing callback"""
        bridge = StreamingBridge(self.config)

        # Mock IFD analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_pressure_metrics.return_value = Mock(
            confidence=0.8,
            expected_direction='LONG',
            strike=21900.0,
            option_type='C'
        )
        bridge.ifd_analyzer = mock_analyzer

        # Mock pressure metrics
        mock_metrics = Mock(
            strike=21900.0,
            option_type='C',
            pressure_ratio=2.5,
            total_volume=1000,
            confidence=0.85
        )

        # Process metrics
        bridge._on_pressure_metrics(mock_metrics)

        # Verify IFD analyzer was called
        mock_analyzer.analyze_pressure_metrics.assert_called_once()

    def test_signal_callback_registration(self):
        """Test signal callback registration and execution"""
        bridge = StreamingBridge(self.config)

        # Track callback execution
        callback_executed = False
        signal_received = None

        def test_callback(signal):
            nonlocal callback_executed, signal_received
            callback_executed = True
            signal_received = signal

        # Register callback
        bridge.register_signal_callback(test_callback)

        # Create mock signal
        mock_signal = Mock(
            confidence=0.9,
            expected_direction='LONG',
            strike=21900.0,
            option_type='C'
        )

        # Trigger callback
        for callback in bridge.signal_callbacks:
            callback(mock_signal)

        # Verify callback was executed
        self.assertTrue(callback_executed)
        self.assertEqual(signal_received, mock_signal)

    def test_development_mode(self):
        """Test development mode with simulated data"""
        config = self.config.copy()
        config['mode'] = 'development'

        bridge = StreamingBridge(config)

        # Should allow streaming even outside market hours in dev mode
        with patch('streaming_bridge.get_eastern_time') as mock_time:
            mock_time.return_value = datetime(2025, 6, 14, 14, 0, 0)  # Saturday
            self.assertTrue(bridge.start_streaming())

    def test_cost_monitoring(self):
        """Test cost monitoring and budget enforcement"""
        bridge = StreamingBridge(self.config)

        # Mock cost monitor
        mock_monitor = Mock()
        mock_monitor.get_daily_total.return_value = 20.0
        mock_monitor.can_continue.return_value = True
        bridge.cost_monitor = mock_monitor

        # Check if streaming can continue
        self.assertTrue(bridge._check_cost_limits())

        # Simulate exceeding budget
        mock_monitor.get_daily_total.return_value = 26.0
        mock_monitor.can_continue.return_value = False

        self.assertFalse(bridge._check_cost_limits())

    def test_create_streaming_bridge_factory(self):
        """Test factory function for creating bridge"""
        bridge = create_streaming_bridge(self.config)

        self.assertIsInstance(bridge, StreamingBridge)
        self.assertEqual(bridge.config['symbols'], ['NQ.OPT'])

    def test_bridge_status_reporting(self):
        """Test bridge status reporting"""
        bridge = StreamingBridge(self.config)

        # Mock components
        bridge.processor = Mock()
        bridge.processor.get_performance_stats.return_value = {
            'metrics': {'events_processed': 1000}
        }

        bridge.pressure_engine = Mock()
        bridge.pressure_engine.get_engine_stats.return_value = {
            'aggregation': {'windows_completed': 50}
        }

        # Get status
        status = bridge.get_bridge_status()

        self.assertFalse(status['is_running'])
        self.assertTrue(status['components_initialized'])
        self.assertIn('processor_stats', status)
        self.assertIn('pressure_stats', status)

    def test_error_handling(self):
        """Test error handling in streaming bridge"""
        bridge = StreamingBridge(self.config)

        # Mock pressure engine to raise error
        bridge.pressure_engine = Mock()
        bridge.pressure_engine.process_mbo_event.side_effect = Exception("Test error")

        # Should handle error gracefully
        with patch('streaming_bridge.logger') as mock_logger:
            bridge._process_mbo_event({'test': 'data'})
            mock_logger.error.assert_called()

    def test_staging_mode_shadow_trading(self):
        """Test staging mode with shadow trading"""
        config = self.config.copy()
        config['mode'] = 'staging'

        bridge = StreamingBridge(config)

        # In staging mode, should track signals but not execute
        self.assertTrue(bridge.shadow_mode)

        # Mock signal
        mock_signal = Mock(
            confidence=0.9,
            expected_direction='LONG'
        )

        # Process signal in shadow mode
        bridge._process_ifd_signal(mock_signal)

        # Should add to shadow signals
        self.assertEqual(len(bridge.shadow_signals), 1)


if __name__ == '__main__':
    unittest.main()
