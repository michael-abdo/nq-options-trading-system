#!/usr/bin/env python3
"""
Cost Control Simulation Tests - Test budget enforcement without live Databento connection
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
import time
from datetime import datetime, timezone, timedelta

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from ..streaming_bridge import StreamingBridge, create_streaming_bridge


class MockUsageMonitor:
    """Mock usage monitor to simulate cost tracking"""

    def __init__(self, daily_budget=25.0):
        self.daily_budget = daily_budget
        self.current_cost = 0.0
        self.start_time = datetime.now(timezone.utc)
        self.data_consumed_mb = 0
        self.events_processed = 0

    def add_cost(self, amount):
        """Simulate adding cost"""
        self.current_cost += amount

    def add_data_usage(self, mb_consumed, events_count):
        """Simulate data usage"""
        self.data_consumed_mb += mb_consumed
        self.events_processed += events_count
        # Simulate cost calculation: $0.01 per MB
        cost = mb_consumed * 0.01
        self.add_cost(cost)

    def get_daily_total(self):
        """Get current daily cost"""
        return self.current_cost

    def can_continue(self):
        """Check if streaming can continue based on budget"""
        return self.current_cost < self.daily_budget

    def should_continue_streaming(self):
        """Check if streaming should continue"""
        return self.can_continue()

    def get_usage_stats(self):
        """Get usage statistics"""
        runtime_hours = (datetime.now(timezone.utc) - self.start_time).total_seconds() / 3600
        return {
            'daily_cost': self.current_cost,
            'daily_budget': self.daily_budget,
            'budget_remaining': self.daily_budget - self.current_cost,
            'runtime_hours': runtime_hours,
            'data_consumed_mb': self.data_consumed_mb,
            'events_processed': self.events_processed,
            'cost_per_hour': self.current_cost / max(runtime_hours, 0.1),
            'budget_utilization': (self.current_cost / self.daily_budget) * 100
        }


class TestCostControlSimulation(unittest.TestCase):
    """Test cost control mechanisms with simulated usage"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'mode': 'development',
            'daily_budget': 25.0,
            'cost_monitoring': True,
            'data_simulation': True
        }

    def test_budget_enforcement_normal_usage(self):
        """Test budget enforcement with normal usage patterns"""
        bridge = StreamingBridge(self.config)

        # Mock the usage monitor
        mock_monitor = MockUsageMonitor(daily_budget=25.0)
        bridge.usage_monitor = mock_monitor

        # Simulate normal streaming usage over time
        for hour in range(8):  # 8 hours of trading
            # Simulate 1 MB per hour usage
            mock_monitor.add_data_usage(mb_consumed=1.0, events_count=1000)

            # Should continue for normal usage ($8 total)
            self.assertTrue(bridge._should_continue_streaming())

        # Check final stats
        stats = mock_monitor.get_usage_stats()
        self.assertEqual(stats['daily_cost'], 8.0)  # $0.01 * 8 MB
        self.assertTrue(stats['budget_remaining'] > 0)

    def test_budget_enforcement_high_usage(self):
        """Test budget enforcement when approaching limits"""
        bridge = StreamingBridge(self.config)

        # Mock the usage monitor with lower budget
        mock_monitor = MockUsageMonitor(daily_budget=10.0)
        bridge.usage_monitor = mock_monitor

        # Simulate high usage that approaches budget
        for i in range(12):  # Consume more than budget allows
            mock_monitor.add_data_usage(mb_consumed=1.0, events_count=1000)

            # Should stop when budget exceeded
            if mock_monitor.get_daily_total() >= 10.0:
                self.assertFalse(bridge._should_continue_streaming())
                break
        else:
            self.fail("Budget enforcement should have stopped streaming")

    def test_cost_monitoring_disabled(self):
        """Test that streaming continues when cost monitoring is disabled"""
        config = self.config.copy()
        config['cost_monitoring'] = False

        bridge = StreamingBridge(config)

        # Mock high usage
        mock_monitor = MockUsageMonitor(daily_budget=1.0)  # Very low budget
        mock_monitor.add_cost(100.0)  # Exceed budget significantly
        bridge.usage_monitor = mock_monitor

        # Should continue when monitoring disabled
        self.assertTrue(bridge._should_continue_streaming())

    def test_emergency_stop_threshold(self):
        """Test emergency stop when budget exceeded by large margin"""
        bridge = StreamingBridge(self.config)

        # Mock the usage monitor
        mock_monitor = MockUsageMonitor(daily_budget=25.0)
        bridge.usage_monitor = mock_monitor

        # Simulate sudden spike in usage (emergency scenario)
        mock_monitor.add_cost(30.0)  # Exceed budget

        # Should trigger emergency stop
        self.assertFalse(bridge._should_continue_streaming())

        stats = mock_monitor.get_usage_stats()
        self.assertGreater(stats['budget_utilization'], 100)

    def test_cost_projection_and_warnings(self):
        """Test cost projection and warning thresholds"""
        bridge = StreamingBridge(self.config)

        mock_monitor = MockUsageMonitor(daily_budget=25.0)
        bridge.usage_monitor = mock_monitor

        # Simulate usage that triggers warnings
        warning_threshold = 15.0  # 60% of budget

        # Gradually increase usage
        while mock_monitor.get_daily_total() < warning_threshold:
            mock_monitor.add_data_usage(mb_consumed=0.5, events_count=500)

        stats = mock_monitor.get_usage_stats()

        # Should be in warning zone
        self.assertGreater(stats['budget_utilization'], 50)
        self.assertLess(stats['budget_utilization'], 100)
        self.assertTrue(mock_monitor.can_continue())

    def test_cost_rate_monitoring(self):
        """Test monitoring of cost accumulation rate"""
        bridge = StreamingBridge(self.config)

        mock_monitor = MockUsageMonitor(daily_budget=25.0)
        bridge.usage_monitor = mock_monitor

        # Simulate 4 hours of usage
        start_time = datetime.now(timezone.utc)
        mock_monitor.start_time = start_time - timedelta(hours=4)
        mock_monitor.add_cost(8.0)  # $2/hour rate

        stats = mock_monitor.get_usage_stats()

        # Check cost rate calculation
        self.assertAlmostEqual(stats['cost_per_hour'], 2.0, places=1)

        # Project daily cost at current rate
        projected_daily = stats['cost_per_hour'] * 24
        self.assertEqual(projected_daily, 48.0)  # Would exceed budget

    def test_budget_reset_simulation(self):
        """Test budget reset at start of new day"""
        bridge = StreamingBridge(self.config)

        # Day 1 - use most of budget
        mock_monitor = MockUsageMonitor(daily_budget=25.0)
        mock_monitor.add_cost(24.0)

        self.assertFalse(mock_monitor.can_continue())

        # Simulate new day - reset budget
        new_monitor = MockUsageMonitor(daily_budget=25.0)
        bridge.usage_monitor = new_monitor

        # Should be able to continue with fresh budget
        self.assertTrue(bridge._should_continue_streaming())

    def test_data_volume_cost_calculation(self):
        """Test cost calculation based on data volume"""
        mock_monitor = MockUsageMonitor(daily_budget=25.0)

        # Test different data volumes
        test_cases = [
            (1.0, 1000, 0.01),   # 1 MB = $0.01
            (10.0, 10000, 0.10), # 10 MB = $0.10
            (100.0, 100000, 1.0) # 100 MB = $1.00
        ]

        for mb_consumed, events_count, expected_cost in test_cases:
            with self.subTest(mb=mb_consumed):
                initial_cost = mock_monitor.get_daily_total()
                mock_monitor.add_data_usage(mb_consumed, events_count)
                actual_cost = mock_monitor.get_daily_total() - initial_cost

                self.assertAlmostEqual(actual_cost, expected_cost, places=2)

    def test_cost_control_integration_with_streaming(self):
        """Test cost control integration with actual streaming simulation"""
        config = self.config.copy()
        config['simulation_interval'] = 0.1  # Fast simulation

        bridge = StreamingBridge(config)

        # Mock components
        mock_monitor = MockUsageMonitor(daily_budget=5.0)  # Low budget
        bridge.usage_monitor = mock_monitor

        # Mock the mbo_client
        bridge.mbo_client = Mock()
        bridge.mbo_client.usage_monitor = mock_monitor

        # Start streaming
        bridge.is_running = True

        # Simulate streaming with cost accumulation
        for i in range(10):
            # Simulate processing cost
            mock_monitor.add_data_usage(mb_consumed=0.6, events_count=600)

            # Check if should continue
            if not bridge._should_continue_streaming():
                break

        # Should have stopped due to budget
        final_cost = mock_monitor.get_daily_total()
        self.assertGreaterEqual(final_cost, 5.0)

    def test_performance_under_cost_pressure(self):
        """Test system performance when approaching budget limits"""
        bridge = StreamingBridge(self.config)

        mock_monitor = MockUsageMonitor(daily_budget=25.0)
        bridge.usage_monitor = mock_monitor

        # Simulate approaching budget limit
        mock_monitor.add_cost(23.0)  # Close to limit

        # System should still function but be cautious
        self.assertTrue(bridge._should_continue_streaming())

        # Add small amount that pushes over
        mock_monitor.add_cost(2.5)  # Now over budget

        # Should stop
        self.assertFalse(bridge._should_continue_streaming())


if __name__ == '__main__':
    # Run with detailed output
    unittest.main(verbosity=2)
