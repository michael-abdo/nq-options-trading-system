#!/usr/bin/env python3
"""
Tests for development and staging modes in streaming bridge
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
import time
from datetime import datetime, timezone

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from ..streaming_bridge import StreamingBridge, create_streaming_bridge


class TestStreamingModes(unittest.TestCase):
    """Test different streaming modes"""

    def test_development_mode_initialization(self):
        """Test development mode setup"""
        config = {
            'mode': 'development',
            'data_simulation': True,
            'market_hours_enforcement': False
        }

        bridge = StreamingBridge(config)

        self.assertEqual(bridge.mode, 'development')
        self.assertTrue(bridge.is_development)
        self.assertFalse(bridge.is_staging)
        self.assertFalse(bridge.is_production)
        self.assertTrue(bridge.use_simulated_data)
        self.assertFalse(bridge.shadow_mode)

    def test_staging_mode_initialization(self):
        """Test staging mode setup"""
        config = {
            'mode': 'staging',
            'shadow_trading': True
        }

        bridge = StreamingBridge(config)

        self.assertEqual(bridge.mode, 'staging')
        self.assertFalse(bridge.is_development)
        self.assertTrue(bridge.is_staging)
        self.assertFalse(bridge.is_production)
        self.assertTrue(bridge.shadow_mode)

    def test_production_mode_initialization(self):
        """Test production mode setup"""
        config = {
            'mode': 'production'
        }

        bridge = StreamingBridge(config)

        self.assertEqual(bridge.mode, 'production')
        self.assertFalse(bridge.is_development)
        self.assertFalse(bridge.is_staging)
        self.assertTrue(bridge.is_production)
        self.assertFalse(bridge.shadow_mode)
        self.assertFalse(bridge.use_simulated_data)

    def test_development_mode_market_hours(self):
        """Test that development mode bypasses market hours check"""
        config = {
            'mode': 'development',
            'market_hours_enforcement': True
        }

        bridge = StreamingBridge(config)

        # Should always return True in development mode
        with patch('streaming_bridge.is_futures_market_hours', return_value=False):
            self.assertTrue(bridge._check_market_hours())

    def test_production_mode_market_hours(self):
        """Test that production mode enforces market hours"""
        config = {
            'mode': 'production',
            'market_hours_enforcement': True
        }

        bridge = StreamingBridge(config)

        # Should respect actual market hours
        with patch('streaming_bridge.is_futures_market_hours', return_value=False):
            self.assertFalse(bridge._check_market_hours())

        with patch('streaming_bridge.is_futures_market_hours', return_value=True):
            self.assertTrue(bridge._check_market_hours())

    def test_development_mode_authentication(self):
        """Test that development mode can skip authentication"""
        config = {
            'mode': 'development',
            'data_simulation': True
        }

        bridge = StreamingBridge(config)

        # Mock components not available
        with patch('streaming_bridge.COMPONENTS_AVAILABLE', False):
            self.assertFalse(bridge._pre_flight_checks())

        # Mock components available
        with patch('streaming_bridge.COMPONENTS_AVAILABLE', True):
            # Should pass even without auth in dev mode
            self.assertTrue(bridge._pre_flight_checks())

    def test_staging_mode_shadow_signals(self):
        """Test shadow signal tracking in staging mode"""
        config = {
            'mode': 'staging'
        }

        bridge = StreamingBridge(config)

        # Create mock signal
        mock_signal = Mock(
            strike=21900.0,
            option_type='C',
            final_confidence=0.85,
            signal_strength=2.5,
            expected_direction='LONG'
        )

        # Process signal
        bridge._process_ifd_signal(mock_signal)

        # Should be in shadow signals, not regular signals
        self.assertEqual(len(bridge.shadow_signals), 1)
        self.assertEqual(bridge.shadow_signals[0], mock_signal)

        # Get shadow signals
        shadow_signals = bridge.get_shadow_signals()
        self.assertEqual(len(shadow_signals), 1)

    def test_development_mode_simulated_data(self):
        """Test simulated data generation in development mode"""
        config = {
            'mode': 'development',
            'data_simulation': True
        }

        bridge = StreamingBridge(config)

        # Mock the IFD analyzer
        bridge.ifd_analyzer = Mock()
        bridge.ifd_analyzer.analyze_pressure_event = Mock(return_value=None)

        # Generate simulated data
        initial_events = bridge.events_processed
        bridge._simulate_streaming_data()

        # Should have processed some events
        self.assertGreater(bridge.events_processed, initial_events)

        # Analyzer should have been called
        bridge.ifd_analyzer.analyze_pressure_event.assert_called()

    def test_mode_specific_status(self):
        """Test that status includes mode-specific information"""
        # Development mode
        dev_config = {'mode': 'development', 'data_simulation': True}
        dev_bridge = StreamingBridge(dev_config)
        dev_status = dev_bridge.get_bridge_status()

        self.assertEqual(dev_status['mode'], 'development')
        self.assertTrue(dev_status['simulated_data'])
        self.assertFalse(dev_status['shadow_mode'])

        # Staging mode
        staging_config = {'mode': 'staging'}
        staging_bridge = StreamingBridge(staging_config)
        staging_status = staging_bridge.get_bridge_status()

        self.assertEqual(staging_status['mode'], 'staging')
        self.assertTrue(staging_status['shadow_mode'])
        self.assertIn('shadow_signals_count', staging_status)

        # Production mode
        prod_config = {'mode': 'production'}
        prod_bridge = StreamingBridge(prod_config)
        prod_status = prod_bridge.get_bridge_status()

        self.assertEqual(prod_status['mode'], 'production')
        self.assertFalse(prod_status['shadow_mode'])
        self.assertFalse(prod_status['simulated_data'])

    def test_streaming_loop_development_mode(self):
        """Test streaming loop behavior in development mode"""
        config = {
            'mode': 'development',
            'data_simulation': True,
            'simulation_interval': 0.1  # Fast for testing
        }

        bridge = StreamingBridge(config)
        bridge.ifd_analyzer = Mock()

        # Start streaming
        with patch('streaming_bridge.COMPONENTS_AVAILABLE', True):
            bridge.start_streaming()

            # Let it run briefly
            time.sleep(0.5)

            # Should have processed events
            self.assertGreater(bridge.events_processed, 0)

            # Stop streaming
            bridge.stop()

    def test_cost_monitoring_bypass_in_development(self):
        """Test that development mode can bypass cost monitoring"""
        config = {
            'mode': 'development',
            'cost_monitoring': True,
            'daily_budget': 0  # Zero budget
        }

        bridge = StreamingBridge(config)

        # Should continue even with zero budget in dev mode
        self.assertTrue(bridge._should_continue_streaming())

    def test_signal_routing_by_mode(self):
        """Test that signals are routed correctly based on mode"""
        # Production mode - normal routing
        prod_bridge = StreamingBridge({'mode': 'production'})
        prod_bridge.ifd_analyzer = Mock()

        mock_metrics = Mock()
        mock_signal = Mock(
            strike=21900.0,
            option_type='C',
            final_confidence=0.9,
            signal_strength=3.0
        )

        prod_bridge.ifd_analyzer.analyze_pressure_event = Mock(return_value=mock_signal)
        prod_bridge._on_pressure_metrics(mock_metrics)

        # Should be in regular signals
        recent_signals = prod_bridge.signal_manager.get_recent_signals()
        self.assertEqual(len(recent_signals), 1)

        # Staging mode - shadow routing
        staging_bridge = StreamingBridge({'mode': 'staging'})
        staging_bridge.ifd_analyzer = Mock()
        staging_bridge.ifd_analyzer.analyze_pressure_event = Mock(return_value=mock_signal)

        staging_bridge._on_pressure_metrics(mock_metrics)

        # Should be in shadow signals
        self.assertEqual(len(staging_bridge.shadow_signals), 1)
        regular_signals = staging_bridge.signal_manager.get_recent_signals()
        self.assertEqual(len(regular_signals), 0)


if __name__ == '__main__':
    unittest.main()
