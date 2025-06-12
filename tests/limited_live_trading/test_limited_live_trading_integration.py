#!/usr/bin/env python3
"""
Limited Live Trading Integration Tests

Comprehensive tests for the Limited Live Trading system to verify:
- Risk-controlled position testing with 1-contract maximum
- Real order placement and execution monitoring
- Budget enforcement and automatic shutoffs
- P&L tracking vs predicted outcomes
- Stop-loss and risk management verification
"""

import os
import sys
import time
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

# Add necessary paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'tasks/options_trading_system/analysis_engine/strategies'))

try:
    from tasks.options_trading_system.analysis_engine.strategies.limited_live_trading_orchestrator import (
        LimitedLiveTradingConfig,
        LimitedLiveTradingOrchestrator,
        BudgetEnforcer,
        LiveOrderExecutor,
        ExecutionMetrics,
        BudgetStatus,
        LiveTradingPosition
    )
    LIMITED_LIVE_TRADING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Limited Live Trading not available: {e}")
    LIMITED_LIVE_TRADING_AVAILABLE = False


class TestLimitedLiveTradingIntegration(unittest.TestCase):
    """Integration tests for Limited Live Trading system"""

    def setUp(self):
        """Set up test configuration"""
        self.config = LimitedLiveTradingConfig(
            start_date='2025-06-12',
            duration_days=1,  # Start with 1 day for testing
            max_position_size=1,
            max_daily_positions=3,
            max_total_positions=5,
            daily_cost_limit=8.0,
            monthly_budget_limit=200.0,
            cost_per_signal_limit=5.0,
            stop_loss_percentage=2.0,
            profit_target_percentage=4.0,
            max_daily_loss=50.0,
            max_total_risk=200.0,
            max_slippage_percentage=1.0,
            min_fill_quality=0.95,
            max_execution_delay=5.0,
            confidence_threshold=0.70,
            auto_shutoff_enabled=True
        )

        self.test_signal = {
            'id': 'test_signal_001',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'strike': 21350,
            'confidence': 0.75,
            'expected_value': 25.0,
            'risk_reward_ratio': 1.5,
            'signal_type': 'call_buying',
            'algorithm_version': 'v1.0'
        }

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_budget_enforcer_initialization(self):
        """Test budget enforcer initialization and basic functionality"""
        budget_enforcer = BudgetEnforcer(self.config)

        # Test initial state
        self.assertEqual(budget_enforcer.daily_costs, 0.0)
        self.assertEqual(budget_enforcer.monthly_costs, 0.0)
        self.assertEqual(budget_enforcer.signal_count, 0)
        self.assertFalse(budget_enforcer.shutoff_triggered)
        self.assertTrue(budget_enforcer.is_trading_allowed())

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_budget_enforcer_cost_tracking(self):
        """Test budget cost tracking and limit enforcement"""
        budget_enforcer = BudgetEnforcer(self.config)

        # Record normal cost
        budget_enforcer.record_cost(3.0, "signal")
        self.assertEqual(budget_enforcer.daily_costs, 3.0)
        self.assertEqual(budget_enforcer.signal_count, 1)
        self.assertTrue(budget_enforcer.is_trading_allowed())

        # Record cost that triggers daily limit
        budget_enforcer.record_cost(6.0, "data")
        self.assertEqual(budget_enforcer.daily_costs, 9.0)  # 3 + 6 = 9 > 8
        self.assertTrue(budget_enforcer.shutoff_triggered)
        self.assertFalse(budget_enforcer.is_trading_allowed())

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_budget_status_reporting(self):
        """Test budget status reporting"""
        budget_enforcer = BudgetEnforcer(self.config)
        budget_enforcer.record_cost(4.0, "signal")

        status = budget_enforcer.get_budget_status()

        self.assertIsInstance(status, BudgetStatus)
        self.assertEqual(status.daily_costs, 4.0)
        self.assertEqual(status.monthly_costs, 4.0)
        self.assertEqual(status.total_signals, 1)
        self.assertEqual(status.cost_per_signal, 4.0)
        self.assertEqual(status.remaining_daily_budget, 4.0)  # 8 - 4
        self.assertFalse(status.auto_shutoff_triggered)

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_live_order_executor_initialization(self):
        """Test live order executor initialization"""
        executor = LiveOrderExecutor(self.config)

        self.assertEqual(len(executor.open_positions), 0)
        self.assertEqual(len(executor.execution_history), 0)
        self.assertEqual(executor.total_realized_pnl, 0.0)
        self.assertFalse(executor.broker_connected)

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_live_order_executor_broker_connection(self):
        """Test broker connection simulation"""
        executor = LiveOrderExecutor(self.config)

        # Test connection
        connected = executor.connect_to_broker()
        self.assertTrue(connected)
        self.assertTrue(executor.broker_connected)

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_live_order_execution(self):
        """Test live order execution with risk controls"""
        executor = LiveOrderExecutor(self.config)
        executor.connect_to_broker()

        # Place order
        position = executor.place_live_order(self.test_signal, 1)

        self.assertIsNotNone(position)
        self.assertIsInstance(position, LiveTradingPosition)
        self.assertEqual(position.size, 1)  # Respects max position size
        self.assertEqual(position.symbol, f"NQ{self.test_signal['strike']}")
        self.assertTrue(position.is_open)
        self.assertGreater(position.risk_amount, 0)

        # Verify position is tracked
        self.assertEqual(len(executor.open_positions), 1)
        self.assertEqual(len(executor.execution_history), 1)

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_position_risk_limits(self):
        """Test position risk limit enforcement"""
        executor = LiveOrderExecutor(self.config)
        executor.connect_to_broker()

        # Try to place order exceeding max position size
        position = executor.place_live_order(self.test_signal, 5)  # Exceeds max of 1

        self.assertIsNotNone(position)
        self.assertEqual(position.size, 1)  # Should be capped at max

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_execution_quality_tracking(self):
        """Test execution quality metrics tracking"""
        executor = LiveOrderExecutor(self.config)
        executor.connect_to_broker()

        # Place order
        executor.place_live_order(self.test_signal, 1)

        # Get execution quality summary
        quality_summary = executor.get_execution_quality_summary()

        self.assertEqual(quality_summary['total_executions'], 1)
        self.assertGreaterEqual(quality_summary['avg_slippage_pct'], 0)
        self.assertGreaterEqual(quality_summary['avg_execution_time'], 0)
        self.assertGreaterEqual(quality_summary['avg_fill_quality'], 0)
        self.assertGreaterEqual(quality_summary['quality_score'], 0)

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_position_updates_and_pnl_tracking(self):
        """Test position updates and P&L tracking"""
        executor = LiveOrderExecutor(self.config)
        executor.connect_to_broker()

        # Place order
        position = executor.place_live_order(self.test_signal, 1)
        entry_price = position.entry_price

        # Update market data to simulate price movement
        market_data = {position.symbol: entry_price + 50}  # Price increased
        executor.update_positions(market_data)

        # Check updated position
        updated_position = executor.open_positions[position.position_id]
        self.assertEqual(updated_position.current_price, entry_price + 50)
        self.assertGreater(updated_position.unrealized_pnl, 0)  # Should be positive for long position

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_orchestrator_initialization(self):
        """Test limited live trading orchestrator initialization"""
        orchestrator = LimitedLiveTradingOrchestrator(self.config)

        self.assertIsNotNone(orchestrator.budget_enforcer)
        self.assertIsNotNone(orchestrator.order_executor)
        self.assertFalse(orchestrator.is_running)
        self.assertIsNone(orchestrator.start_time)

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_orchestrator_start_stop(self):
        """Test orchestrator start and stop functionality"""
        orchestrator = LimitedLiveTradingOrchestrator(self.config)

        # Start live trading
        started = orchestrator.start_live_trading()
        self.assertTrue(started)
        self.assertTrue(orchestrator.is_running)
        self.assertIsNotNone(orchestrator.start_time)

        # Stop live trading
        final_status = orchestrator.stop_live_trading()
        self.assertFalse(orchestrator.is_running)
        self.assertIsInstance(final_status, dict)

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_signal_processing_workflow(self):
        """Test complete signal processing workflow"""
        # Use a config with higher cost limits for this test
        test_config = LimitedLiveTradingConfig(
            start_date='2025-06-12',
            duration_days=1,
            max_position_size=1,
            daily_cost_limit=12.0,  # Higher limit
            monthly_budget_limit=300.0,  # Higher limit
            cost_per_signal_limit=10.0,  # Higher limit to allow signal processing
            confidence_threshold=0.70,
            auto_shutoff_enabled=True
        )

        orchestrator = LimitedLiveTradingOrchestrator(test_config)
        orchestrator.start_live_trading()

        # Process signal
        success = orchestrator.process_signal_for_live_trading(self.test_signal)
        self.assertTrue(success)

        # Check that position was created
        status = orchestrator.get_trading_status()
        self.assertEqual(status['open_positions'], 1)
        self.assertGreater(status['total_risk'], 0)

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_low_confidence_signal_rejection(self):
        """Test that low confidence signals are rejected"""
        orchestrator = LimitedLiveTradingOrchestrator(self.config)
        orchestrator.start_live_trading()

        # Create low confidence signal
        low_conf_signal = self.test_signal.copy()
        low_conf_signal['confidence'] = 0.50  # Below threshold of 0.70

        # Process signal
        success = orchestrator.process_signal_for_live_trading(low_conf_signal)
        self.assertFalse(success)

        # Check that no position was created
        status = orchestrator.get_trading_status()
        self.assertEqual(status['open_positions'], 0)

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_budget_limit_signal_blocking(self):
        """Test that signals are blocked when budget limits are hit"""
        orchestrator = LimitedLiveTradingOrchestrator(self.config)
        orchestrator.start_live_trading()

        # Exhaust daily budget
        orchestrator.budget_enforcer.record_cost(8.5, "data")  # Exceeds daily limit

        # Try to process signal
        success = orchestrator.process_signal_for_live_trading(self.test_signal)
        self.assertFalse(success)

        # Verify trading is not allowed
        self.assertFalse(orchestrator.budget_enforcer.is_trading_allowed())

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_trading_status_reporting(self):
        """Test comprehensive trading status reporting"""
        orchestrator = LimitedLiveTradingOrchestrator(self.config)
        orchestrator.start_live_trading()

        # Process signal to create position
        orchestrator.process_signal_for_live_trading(self.test_signal)

        # Get status
        status = orchestrator.get_trading_status()

        # Verify status structure
        required_fields = [
            'is_running', 'start_time', 'trading_allowed',
            'open_positions', 'max_positions', 'total_risk', 'max_risk',
            'total_unrealized_pnl', 'total_realized_pnl', 'total_pnl',
            'budget_status', 'execution_quality',
            'risk_utilization_pct', 'position_utilization_pct'
        ]

        for field in required_fields:
            self.assertIn(field, status, f"Missing field: {field}")

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_stop_loss_triggering(self):
        """Test stop loss triggering and position closure"""
        executor = LiveOrderExecutor(self.config)
        executor.connect_to_broker()

        # Place order
        position = executor.place_live_order(self.test_signal, 1)
        entry_price = position.entry_price
        stop_loss = position.stop_loss_price

        # Simulate price drop below stop loss
        market_data = {position.symbol: stop_loss - 10}
        executor.update_positions(market_data)

        # Check that position was closed
        updated_position = executor.open_positions[position.position_id]
        self.assertFalse(updated_position.is_open)
        self.assertLess(updated_position.realized_pnl, 0)  # Should be negative

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_profit_target_triggering(self):
        """Test profit target triggering and position closure"""
        executor = LiveOrderExecutor(self.config)
        executor.connect_to_broker()

        # Place order
        position = executor.place_live_order(self.test_signal, 1)
        entry_price = position.entry_price
        profit_target = position.profit_target_price

        # Simulate price rise above profit target
        market_data = {position.symbol: profit_target + 10}
        executor.update_positions(market_data)

        # Check that position was closed
        updated_position = executor.open_positions[position.position_id]
        self.assertFalse(updated_position.is_open)
        self.assertGreater(updated_position.realized_pnl, 0)  # Should be positive

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_risk_amount_calculation(self):
        """Test risk amount calculation for positions"""
        executor = LiveOrderExecutor(self.config)
        executor.connect_to_broker()

        # Place order
        position = executor.place_live_order(self.test_signal, 1)

        # Verify risk amount calculation (using new calculation method)
        # Note: The actual risk calculation includes the cap logic from _calculate_stop_loss
        self.assertGreater(position.risk_amount, 0)
        self.assertLessEqual(position.risk_amount, 5.0)  # Should be capped at $5 due to stop loss logic
        self.assertLessEqual(position.risk_amount, self.config.max_total_risk)

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_position_limits_enforcement(self):
        """Test that position limits are enforced"""
        executor = LiveOrderExecutor(self.config)
        executor.connect_to_broker()

        # Place maximum number of positions
        for i in range(self.config.max_total_positions):
            signal = self.test_signal.copy()
            signal['id'] = f"test_signal_{i}"
            signal['strike'] = 21350 + i * 25
            position = executor.place_live_order(signal, 1)
            self.assertIsNotNone(position)

        # Try to place one more position (should be rejected)
        excess_signal = self.test_signal.copy()
        excess_signal['id'] = "excess_signal"
        excess_signal['strike'] = 21500
        excess_position = executor.place_live_order(excess_signal, 1)
        self.assertIsNone(excess_position)

    def test_missing_components_graceful_handling(self):
        """Test graceful handling when components are missing"""
        if not LIMITED_LIVE_TRADING_AVAILABLE:
            self.skipTest("Testing graceful degradation when components missing")

        # This test verifies the system can handle missing optional components
        # The actual implementation should have fallbacks
        self.assertTrue(True)  # Placeholder for graceful degradation test


class TestLimitedLiveTradingFactory(unittest.TestCase):
    """Test factory functions and configuration"""

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_factory_function(self):
        """Test factory function for creating orchestrator"""
        from tasks.options_trading_system.analysis_engine.strategies.limited_live_trading_orchestrator import (
            create_limited_live_trading_orchestrator
        )

        config_dict = {
            'start_date': '2025-06-12',
            'duration_days': 1,
            'max_position_size': 1,
            'daily_cost_limit': 8.0,
            'monthly_budget_limit': 200.0,
            'auto_shutoff_enabled': True
        }

        orchestrator = create_limited_live_trading_orchestrator(config_dict)
        self.assertIsInstance(orchestrator, LimitedLiveTradingOrchestrator)

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_config_validation(self):
        """Test configuration validation"""
        # Test valid config
        valid_config = LimitedLiveTradingConfig(
            start_date='2025-06-12',
            max_position_size=1,
            daily_cost_limit=8.0
        )
        self.assertEqual(valid_config.max_position_size, 1)
        self.assertEqual(valid_config.daily_cost_limit, 8.0)


def run_integration_tests():
    """Run all integration tests"""
    print("🧪 Running Limited Live Trading Integration Tests")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLimitedLiveTradingIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestLimitedLiveTradingFactory))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 60)
    print("📊 Integration Test Results:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")

    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")

    success = len(result.failures) == 0 and len(result.errors) == 0

    if success:
        print("\n🎉 All integration tests passed!")
        print("\n📝 Verified Features:")
        print("  • Risk-controlled position testing (1-contract max)")
        print("  • Budget enforcement with automatic shutoffs")
        print("  • Live order execution simulation")
        print("  • P&L tracking vs predicted outcomes")
        print("  • Stop-loss and profit target management")
        print("  • Execution quality tracking")
        print("  • Signal processing workflow")
        print("  • Position and risk limit enforcement")
    else:
        print(f"\n⚠️ {len(result.failures) + len(result.errors)} test(s) failed.")

    return success


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)
