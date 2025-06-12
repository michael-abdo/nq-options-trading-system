#!/usr/bin/env python3
"""
System Resilience and Stress Testing

Comprehensive stress tests for system resilience:
- High-frequency error scenarios and system stability
- Memory and resource exhaustion handling
- Concurrent operation stress testing
- System recovery under extreme conditions
- Performance degradation graceful handling
"""

import os
import sys
import time
import threading
import unittest
import gc
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        LiveOrderExecutor
    )
    LIMITED_LIVE_TRADING_AVAILABLE = True
except ImportError:
    LIMITED_LIVE_TRADING_AVAILABLE = False

try:
    from tasks.options_trading_system.analysis_engine.strategies.production_error_handler import (
        ProductionErrorHandler,
        ErrorSeverity
    )
    PRODUCTION_ERROR_HANDLER_AVAILABLE = True
except ImportError:
    PRODUCTION_ERROR_HANDLER_AVAILABLE = False


class TestHighFrequencyErrors(unittest.TestCase):
    """Test system stability under high-frequency error conditions"""

    def setUp(self):
        """Set up test configuration"""
        self.config = LimitedLiveTradingConfig(
            start_date='2025-06-12',
            duration_days=1,
            max_position_size=1,
            daily_cost_limit=20.0,  # Higher for stress testing
            monthly_budget_limit=500.0,
            auto_shutoff_enabled=True
        )

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_rapid_signal_processing_stability(self):
        """Test system stability under rapid signal processing"""
        orchestrator = LimitedLiveTradingOrchestrator(self.config)
        orchestrator.start_live_trading()

        # Generate many signals rapidly
        signals = []
        for i in range(50):
            signal = {
                'id': f'stress_signal_{i}',
                'strike': 21350 + (i % 10) * 25,
                'confidence': 0.75 + (i % 5) * 0.05,
                'expected_value': 20.0 + (i % 10) * 5,
                'signal_type': 'call_buying' if i % 2 == 0 else 'put_buying'
            }
            signals.append(signal)

        # Process signals rapidly
        successful_trades = 0
        failed_trades = 0
        errors = []

        start_time = time.time()
        for signal in signals:
            try:
                success = orchestrator.process_signal_for_live_trading(signal)
                if success:
                    successful_trades += 1
                else:
                    failed_trades += 1

                # Brief delay to avoid overwhelming system
                time.sleep(0.01)

            except Exception as e:
                errors.append(str(e))
                failed_trades += 1

            # Stop if budget exhausted (expected behavior)
            if not orchestrator.budget_enforcer.is_trading_allowed():
                break

        processing_time = time.time() - start_time

        # System should remain stable
        self.assertLess(len(errors), 5)  # Should have minimal errors
        self.assertGreater(processing_time, 0)  # Should complete processing

        # Get final status
        final_status = orchestrator.get_trading_status()
        self.assertIsNotNone(final_status)
        self.assertTrue(final_status['is_running'])

        print(f"Processed {len(signals)} signals: {successful_trades} successful, {failed_trades} failed, {len(errors)} errors")

    @unittest.skipUnless(PRODUCTION_ERROR_HANDLER_AVAILABLE, "Production Error Handler not available")
    def test_error_handler_under_high_load(self):
        """Test error handler performance under high error load"""
        error_handler = ProductionErrorHandler()
        error_handler.start_monitoring()

        # Generate many errors rapidly
        error_count = 100
        start_time = time.time()

        for i in range(error_count):
            error_handler.record_error(
                component=f"test_component_{i % 5}",
                error_type="STRESS_TEST_ERROR",
                message=f"Stress test error #{i}",
                severity=ErrorSeverity.MEDIUM if i % 3 != 0 else ErrorSeverity.HIGH,
                context={"test_iteration": i, "stress_test": True}
            )

        processing_time = time.time() - start_time

        # System should handle high error load
        self.assertLess(processing_time, 5.0)  # Should process quickly
        self.assertEqual(len(error_handler.error_history), error_count)

        # Health report should still be accessible
        health_report = error_handler.get_system_health()
        self.assertIsNotNone(health_report)
        self.assertGreater(health_report['recent_errors'], 0)

        error_handler.stop_monitoring()
        print(f"Processed {error_count} errors in {processing_time:.2f}s")


class TestResourceExhaustionHandling(unittest.TestCase):
    """Test handling of resource exhaustion scenarios"""

    def setUp(self):
        """Set up test configuration"""
        self.config = LimitedLiveTradingConfig(
            start_date='2025-06-12',
            duration_days=1,
            max_position_size=1,
            daily_cost_limit=8.0,
            monthly_budget_limit=200.0,
            auto_shutoff_enabled=True
        )

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_memory_usage_stability(self):
        """Test memory usage stability under prolonged operation"""
        orchestrator = LimitedLiveTradingOrchestrator(self.config)
        orchestrator.start_live_trading()

        # Monitor memory usage (skip if psutil not available)
        try:
            import psutil
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_monitoring_available = True
        except ImportError:
            initial_memory = 0
            memory_monitoring_available = False

        # Run many operations
        for i in range(100):
            test_signal = {
                'id': f'memory_test_signal_{i}',
                'strike': 21350 + (i % 20) * 25,
                'confidence': 0.60,  # Below threshold to avoid actual trading
                'expected_value': 15.0,
                'signal_type': 'call_buying'
            }

            # This should be rejected due to low confidence, but still process
            orchestrator.process_signal_for_live_trading(test_signal)

            # Periodic garbage collection
            if i % 20 == 0:
                gc.collect()

        if memory_monitoring_available:
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_growth = final_memory - initial_memory

            # Memory growth should be reasonable
            self.assertLess(memory_growth, 50)  # Less than 50MB growth
            print(f"Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB (+{memory_growth:.1f}MB)")
        else:
            print("Memory monitoring skipped - psutil not available")

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_position_limit_enforcement(self):
        """Test strict position limit enforcement under pressure"""
        # Use config with very low limits
        strict_config = LimitedLiveTradingConfig(
            start_date='2025-06-12',
            duration_days=1,
            max_position_size=1,
            max_total_positions=2,  # Very low limit
            daily_cost_limit=20.0,
            monthly_budget_limit=500.0,
            auto_shutoff_enabled=True
        )

        orchestrator = LimitedLiveTradingOrchestrator(strict_config)
        orchestrator.start_live_trading()

        # Try to create many positions
        successful_positions = 0
        for i in range(10):
            test_signal = {
                'id': f'position_limit_test_{i}',
                'strike': 21350 + i * 25,
                'confidence': 0.75,
                'expected_value': 25.0,
                'signal_type': 'call_buying'
            }

            success = orchestrator.process_signal_for_live_trading(test_signal)
            if success:
                successful_positions += 1

        # Should respect strict position limits
        status = orchestrator.get_trading_status()
        self.assertLessEqual(status['open_positions'], strict_config.max_total_positions)
        self.assertLessEqual(successful_positions, strict_config.max_total_positions)

        print(f"Created {successful_positions} positions (limit: {strict_config.max_total_positions})")


class TestConcurrentOperationStress(unittest.TestCase):
    """Test system under concurrent operation stress"""

    def setUp(self):
        """Set up test configuration"""
        self.config = LimitedLiveTradingConfig(
            start_date='2025-06-12',
            duration_days=1,
            max_position_size=1,
            daily_cost_limit=50.0,  # Higher for concurrent testing
            monthly_budget_limit=1000.0,
            auto_shutoff_enabled=True
        )

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_concurrent_signal_processing(self):
        """Test concurrent signal processing"""
        orchestrator = LimitedLiveTradingOrchestrator(self.config)
        orchestrator.start_live_trading()

        def process_signal_batch(batch_id):
            """Process a batch of signals"""
            results = []
            for i in range(10):
                signal = {
                    'id': f'concurrent_signal_{batch_id}_{i}',
                    'strike': 21350 + (batch_id * 100) + (i * 25),
                    'confidence': 0.75,
                    'expected_value': 20.0 + i * 2,
                    'signal_type': 'call_buying' if i % 2 == 0 else 'put_buying'
                }

                try:
                    success = orchestrator.process_signal_for_live_trading(signal)
                    results.append(('success' if success else 'failed', signal['id']))
                except Exception as e:
                    results.append(('error', str(e)))

                time.sleep(0.01)  # Brief delay

            return results

        # Run concurrent batches
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(process_signal_batch, i) for i in range(3)]

            all_results = []
            for future in as_completed(futures):
                try:
                    batch_results = future.result(timeout=10)
                    all_results.extend(batch_results)
                except Exception as e:
                    all_results.append(('batch_error', str(e)))

        # Analyze results
        successful = len([r for r in all_results if r[0] == 'success'])
        failed = len([r for r in all_results if r[0] == 'failed'])
        errors = len([r for r in all_results if r[0] == 'error'])

        # System should handle concurrent operations
        self.assertGreater(len(all_results), 0)
        self.assertLess(errors, len(all_results) * 0.1)  # Less than 10% errors

        print(f"Concurrent processing: {successful} successful, {failed} failed, {errors} errors")

    @unittest.skipUnless(PRODUCTION_ERROR_HANDLER_AVAILABLE, "Production Error Handler not available")
    def test_concurrent_error_reporting(self):
        """Test concurrent error reporting and handling"""
        error_handler = ProductionErrorHandler()
        error_handler.start_monitoring()

        def generate_errors_concurrently(thread_id):
            """Generate errors from multiple threads"""
            errors_generated = []
            for i in range(20):
                try:
                    error_id = error_handler.record_error(
                        component=f"concurrent_component_{thread_id}",
                        error_type="CONCURRENT_ERROR",
                        message=f"Thread {thread_id} error {i}",
                        severity=ErrorSeverity.MEDIUM,
                        context={"thread_id": thread_id, "error_index": i}
                    )
                    errors_generated.append(error_id)
                    time.sleep(0.005)  # Small delay
                except Exception as e:
                    errors_generated.append(f"error: {e}")
            return errors_generated

        # Run concurrent error generation
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(generate_errors_concurrently, i) for i in range(4)]

            all_error_ids = []
            for future in as_completed(futures):
                try:
                    thread_errors = future.result(timeout=10)
                    all_error_ids.extend(thread_errors)
                except Exception as e:
                    print(f"Thread error: {e}")

        # Verify error handling
        self.assertGreater(len(all_error_ids), 70)  # Should have most errors recorded
        self.assertGreater(len(error_handler.error_history), 70)

        # Health report should be accessible
        health_report = error_handler.get_system_health()
        self.assertIsNotNone(health_report)

        error_handler.stop_monitoring()
        print(f"Concurrent errors generated: {len(all_error_ids)}")


class TestExtremeConditionRecovery(unittest.TestCase):
    """Test system recovery under extreme conditions"""

    def setUp(self):
        """Set up test configuration"""
        self.config = LimitedLiveTradingConfig(
            start_date='2025-06-12',
            duration_days=1,
            max_position_size=1,
            daily_cost_limit=8.0,
            monthly_budget_limit=200.0,
            auto_shutoff_enabled=True
        )

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_system_restart_recovery(self):
        """Test system recovery after simulated restart"""
        # First session
        orchestrator1 = LimitedLiveTradingOrchestrator(self.config)
        orchestrator1.start_live_trading()

        # Create some state
        test_signal = {
            'id': 'restart_test_signal',
            'strike': 21350,
            'confidence': 0.75,
            'expected_value': 25.0,
            'signal_type': 'call_buying'
        }

        success1 = orchestrator1.process_signal_for_live_trading(test_signal)
        status1 = orchestrator1.get_trading_status()

        # Simulate shutdown
        orchestrator1.stop_live_trading()

        # Second session (simulated restart)
        orchestrator2 = LimitedLiveTradingOrchestrator(self.config)
        orchestrator2.start_live_trading()

        # Should be able to operate normally
        success2 = orchestrator2.process_signal_for_live_trading(test_signal)
        status2 = orchestrator2.get_trading_status()

        # Both sessions should work independently
        self.assertIsNotNone(status1)
        self.assertIsNotNone(status2)
        self.assertTrue(status2['is_running'])

        orchestrator2.stop_live_trading()

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_rapid_start_stop_cycles(self):
        """Test rapid start/stop cycles"""
        cycles_completed = 0
        errors = []

        for i in range(5):
            try:
                orchestrator = LimitedLiveTradingOrchestrator(self.config)

                # Start
                start_success = orchestrator.start_live_trading()
                self.assertTrue(start_success)

                # Brief operation
                test_signal = {
                    'id': f'cycle_test_signal_{i}',
                    'strike': 21350,
                    'confidence': 0.60,  # Below threshold
                    'expected_value': 15.0,
                    'signal_type': 'call_buying'
                }

                orchestrator.process_signal_for_live_trading(test_signal)

                # Stop
                final_status = orchestrator.stop_live_trading()
                self.assertIsNotNone(final_status)

                cycles_completed += 1
                time.sleep(0.1)  # Brief delay between cycles

            except Exception as e:
                errors.append(str(e))

        # Should complete most cycles successfully
        self.assertGreaterEqual(cycles_completed, 4)
        self.assertLess(len(errors), 2)

        print(f"Completed {cycles_completed}/5 start/stop cycles, {len(errors)} errors")


def run_system_resilience_tests():
    """Run all system resilience tests"""
    print("🧪 Running System Resilience and Stress Tests")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestHighFrequencyErrors,
        TestResourceExhaustionHandling,
        TestConcurrentOperationStress,
        TestExtremeConditionRecovery
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print(f"\n📊 System Resilience Tests: {result.testsRun} run, {len(result.failures)} failures, {len(result.errors)} errors")

    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == "__main__":
    success = run_system_resilience_tests()
    exit(0 if success else 1)
